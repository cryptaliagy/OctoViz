# OctoViz

A tool to visualize PR lifetime data from Github!

Before using, ensure you have a github OAuth token to use. Create profiles using `octoviz profile create` to specify the url to connect to (if in corporate environment) and the token to use.

To install, simply use `pip install .`. A virtual environment is strongly encouraged if developing, or if there is a concern for conflicting dependencies with your system.

Cached files and generated HTML files are found in the home directory under the folder '.octoviz' in the home directory. Commands are included to flush the cache, the html files, or everything, as well as to create/delete/update profiles.

Windows support is currently experimental but presumed to be complete.

# Quick Reference Guide

Create a profile
```bash
octoviz profile create -t your_token
```

Edit a profile
```bash
octoviz profile edit -t new_token profile_name
```

Delete a profile
```bash
octoviz profile delete profile_name
```

Basic command
```bash
octoviz run org_name/repo_name [org_name/repo_name ...] # 12 months of data, aggregated by week PR was closed in
```

Force-fetch data and build cache
```
octoviz run -b org_name/repo_name
```

Force-fetch data and do not build cache
```
octoviz run --no-cache org_name/repo_name
```

Clean up all cached data after execution
```
octoviz run -c org_name/repo_name
```

Do not render HTML file (fetches data if cache does not exist)
```
octoviz run --no-render org_name/repo_name
```

Aggregate data by month instead of by week
```
octoviz run -m org_name/repo_name
```

Group data by when the PR was created
```
octoviz run --group-by created org_name/repo_name
```

Show only data for complete time periods
```
octoviz run --complete org_name/repo_name
```

Give a custom name to the output file
```
octoviz run -n my_rendered_file org_name/repo_name
```

Link the x axes of all rendered graphs
```
octoviz run -x org_name/repo_name
```

Link the y axes of all rendered graphs of the same type
```
octoviz run -y org_name/repo_name
```

Show lines for the 10th, 30th, 60th and 95th percentile times
```
octoviz run -p 10,30,60,95 org_name/repo_name
```

# *OctoViz Tour*

## Installation
To install, simply clone this repository and install with `pip install .`


## Creating a Profile
If you are trying to create a profile in OctoViz you will need to use a Github Personal Access token. You can find more information about it in [this link](https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line).

Your Github token will need to have (at minimum) access to Public Repositories (repo:public_repo), but if you want to get data for private repositories you might need to give full control of private repositories (repo) access.

Now that you have your access token, you can create your profile by using the following command:

```
octoviz profile create -t your_token_from_github
```

If you need to use multiple profiles – such as if multiple accounts with private repositories need to be analyzed or if connecting both to Github.com and your corporate's Github repository, you will need to name your profiles. If you only have one profile, you can omit the name; OctoViz will automatically name it 'default' for you.

To name an OctoViz profile, simply add the `-n` flag to your `profile create` call.

```
octoviz profile create -t your_token_from_github -n my_first_profile
```

If you need to connect to a Github Enterprise server, make sure you also pass that to the OctoViz:

```
octoviz profile create -u https://link-to-company-github.com -t your_token_from_github -n work_profile
```
\
If your token was valid, you should now have at least one profile active! Unless you need to update your API token, or the URL to connect to, this should be a one-time setup. You can update your profile by using `octoviz profile update [-t new_token] [-u new_url] NAME`

You can check your profiles by using `octoviz profile --list`.  

## Deleting OctoViz Profile

To delete OctoViz profiles, simply run:

```
octoviz profile delete PROFILE_NAME [PROFILE_NAME ...]
```

You may specify more than one profile name to delete multiple profiles with one command

-------

## Running the OctoViz – Simple
OctoViz was designed to be as simple as possible to use, while still being flexible and powerful enough to provide more detailed usage when desired. The commands and flags shown below will give you a pretty good glimpse of what OctoViz can do!

### **Basic Command & Cache Management**
Without any flags, OctoViz will search for the specified repository in all profiles until it finds it or runs out of profiles to search in. This means that, if you specify multiple repositories from different servers that you have a profile for, you can effectively grab the data from all of them with no extra hassle.

To start, run the following:
```bash
octoviz run org_name/repo_name  # Replace org_name and repo_name with the appropriate info
```

This will cause the OctoViz to connect to Github and pull data of closed pull requests in the repository. By default, it will fetch pull requests that were created within the last 12 months, but you may specify different amounts of time with flags that will be discussed later.

>Extra reading: The pull request data obtained by this method is the 'ShortPullRequest'. You can read more about the data it contains [here](https://github3py.readthedocs.io/en/master/api-reference/pulls.html)

After fetching the data, it will group it by the week that the pull request was closed, and then render two graphs: One is a line chart of the 25th, 50th (median), and 90th percentile time taken to close a pull request in a given week, and the other will be the number of pull requests closed during that week.

To speed up the processing of the same data between OctoViz usages, a local cache will be created and can be found in your OctoViz directory under the folder `cache`. If you re-run the same command, you will see that the time it takes to re-create the graphs is a lot smaller than it took to gather them the first time.

>*Note*: OctoViz will always use cached data if it exists.

If you have previously cached data for a repository and want to re-cache the data, simply specify the flag `-b` or `--build-cache` as shown below:

```bash
octoviz run -b org_name/repo_name # Replace org_name and repo_name with appropriate info
```

This will force OctoViz to poll Github for the newest PR data.

If you do not wish to build a cache at all, specify the `--no-cache` flag when executing the OctoViz as such:

```bash
octoviz run --no-cache org_name/repo_name
```

If you want **all** cached data to be deleted after executing OctoViz, specify the `-c` or `--cleanup` flag as such:
```bash
octoviz run -c org_name/repo_name # Replace org_name and repo_name with appropriate info
```

