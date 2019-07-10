from pathlib import Path
import os, sys, json
import arrow, github3

# Global constants
home_dir = str(Path.home())
octoviz_dir = lambda x="": '%s/.octoviz%s' % (home_dir, "/%s" % x if x else "")
clients = []

def create_directory(dir):
    exists = []
    create = dir.split('/')

    for di in create:
        path = '/'.join(exists + [di])
        if not os.path.exists(octoviz_dir(path)):
            os.mkdir(octoviz_dir(path))
        exists.append(di)

def make_github_client(profile):
    token = profile['token']
    url = profile['url']
    try:
        if url:
            client = github3.enterprise_login(token=token, url=url)
        else:
            client = github3.login(token=token)

        if client is None:
            raise(Exception())
    except Exception as e:
        sys.stderr.write("\nError performing login to Github!\n")
        sys.stderr.write("Check the token or url for login of profile %s\n\n" % profile['name'])
        raise(e)  ## Re-raise the exception to handle it somewhere else in the stack
    
    return client

def get_raw_pull_data(organization, repository, rate_limit, full):
    if rate_limit:
        frame = rate_limit[0][:-1]
        shift = {rate_limit[0]: rate_limit[1]}
        limited = arrow.now().shift(**shift).floor(frame)
    else:
        limited = None
    repo = None
    for client in clients:
        try:
            repo = client.repository(organization, repository)
            break  # Found the repo, stop searching
        except Exception as e:
            continue  # Try the next client
    
    if repo is None:
        return None  # Can't find it under any of the profiles, return None
    pull_requests = repo.pull_requests(state='closed')

    result = []
    for pull_request in pull_requests:
        if limited is not None and arrow.get(pull_request.created_at).floor(frame) <= limited:
            break

        try:
            if full:
                pull_dict = repo.pull_request(pull_request.number).as_dict()  # Get the full data
            else:
                pull_dict = pull_request.as_dict()
        except Exception as e:
            continue
        
        
        result.append(pull_dict)

    return result

def load_profile(name):
    if name[-8:] == '.profile':
        path = octoviz_dir('profiles/%s' % name)
    else:
        path = octoviz_dir('profiles/%s.profile' % name)
    if not os.path.exists(path):
        sys.stderr.write('Profile does not exist!\n')
        sys.exit(1)

    with open(path, 'r') as f:
        profile = json.load(f)
    
    return profile


def write_profile(profile):
    name = profile['name']
    path = octoviz_dir('profiles/%s.profile' % name)

    with open(path, 'w') as f:
        json.dump(profile, f)


def get_all_profiles():
    path = octoviz_dir('profiles/')
    if not os.path.exists(path):
        return []
    _, _, profiles = next(os.walk(path))

    return profiles

def clients_from_profiles():
    profiles = map(lambda x: load_profile(x), get_all_profiles())
    for profile in profiles:
        try:
            clients.append(make_github_client(profile))  # Add to the global space client list for shared access
        except Exception:
            sys.stderr.write('Error connecting to client from profile %s, skipping...\n' % profile['name'])
                