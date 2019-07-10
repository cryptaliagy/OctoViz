# OctoViz

A tool to visualize PR lifetime data from Github!

Before using, ensure you have a github OAuth token to use. Create profiles using `octoviz profile create` to specify the url to connect to (if in corporate environment) and the token to use.

To install, simply use `pip install .`. A virtual environment is strongly encouraged if developing, or if there is a concern for conflicting dependencies with your system.

OctoViz comes with lots of information in the help menu. See `octoviz -h` for more details. All sub-commands also have their own help menu by passing the `-h` flag.

Cached files and generated HTML files are found in the home directory under the folder '.octoviz' in the home directory. Commands are included to flush the cache, the html files, or everything, as well as to create/delete/update profiles.

Windows support is currently experimental but presumed to be complete.

# Table of Contents
1. [OctoViz Tour](#octoviz-tour)
    1. [Installatiion](#installation)
    2. [Creating a Profile](#creating-a-profile)
    3. [Deleting OctoViz Profile](#deleting-octoviz-profile)
    4. [Running the OctoViz – Simple](#running-the-OctoViz-–-simple)
        1. [Basic Commands & Cache Management](#basic-commands-&-cache-management)
        2. [Rate Limiting](#rate-limiting)
        3. [Saving & Customizing Your Graphs](#saving-&-customizing-your-graphs)
        4. [Putting It All Together – Combined Examples](#putting-it-all-together-–-combined-examples)
2. [Quick Reference Guide](#quick-reference-guide)

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

### *Basic Commands & Cache Management*
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

There are some cases in which you might want OctoViz to cache some data but not need it to immediately display any graphs. In this case, the `--no-render` flag can be specified to speed the process along by performing only the caching operations and none of the data processing ones. You can do so as such:

```bash
octoviz run --no-render org_name/repo_name
```

> *Note*: OctoViz does not force the cache to be *re*built when --no-render is specified. If you want to ensure you're fetching the newest data, make sure you also pass the `-b` flag.



### *Rate Limiting*

There may be times when the default settings for OctoViz do not poll enough data or poll too much data for your usage. In that case, you may use the rate limiting arguments to request more data or less data.

The two examples below outline a rate limit of 6 weeks and 6 months respectively:

```
octoviz run --limit-by-weeks 6 org_name/repo_name
octoviz run --limit-by-months 6 org_name/repo_name
```

> *Note*: When rate limiting cached data, OctoViz does not ensure that the data you have is complete. If you have less cached data than you would like to rate-limit, make sure to pass the `-b` flag, otherwise it might show an incomplete graph

There could also be need to see the entire history of a repository's data. In that case, you may specify the `--no-limit` flag when building the cache to grab the full history. Depending on the size of the repository and how active it is in terms of PRs, this could mean a many-year, multi-thousand-call endeavor. Expect this to take a long time, and be wary of possibly surpassing the Github API request limits

```
octoviz run --no-limit org_name/repo_name
```

> *Note*: Github has a limit of 5000 requests per hour to its API. Ensure your calls stay below it.

### *Saving & Customizing Your Graphs*

You may have need to create multiple HTML files for different types of graphs. Should that be the case, you may want to keep all rendered HTML files instead of overriding each one. To do so, make sure to specify a name for the output file with `-n`:

```
octoviz run -n my_repo_graph org_name/repo_name
```

This will produce a file called `'my_repo_graph.html'` in your `'.octoviz/html'` folder. By default, any time OctoViz is run without the `-n` or the `--no-render` flag it will generate a file called `'octoviz.html'` in your `'.octoviz/html'` folder.

When rendering graphs of time-aggregated data, if you would like to group by month instead of by week, it is possible to do so by specifying the `-m` flag as such:

```
octoviz run -m org_name/repo_name
```

If instead of the week/month closed, you would like the data to be grouped by the week/month a PR was created, you may specify the `--group-by` argument as such:

```
octoviz run --group-by created org_name/repo_name
```

When the two graphs for each repository are rendered, you may notice that zooming in or panning the x-axis of one graph will cause the other to also change in an identical way on the x-axis. This allows for quick visual identification of both the current values of the line graph and the number of pull requests on the bar graph.

For two or more repositories, this behaviour is only shared between the graphs of the same repository by default. If you would like to have this behaviour shared between all graphs (so that all graphs are 'synced' to the same timeframe or line number count), specify the `-x` flag.

```
octoviz run -x org_name/repo_name-1 org_name/repo_name-2
```

You may also have noticed that the y-axis scales tend to be different for graphs of different repositories. If you would like to ensure that y-axis panning, zooming, and scale are shared between all graphs in the same column, specify the `-y` flag.

```
octoviz run -y org_name/repo_name-1 org_name/repo_name-2
```

This can be combined with the `-x` flag to always see graphs at the same scale and time in one document

Given that OctoViz collects the most recent data possible, you might notice that the current timeframe is also included in this. If you would like to only see 'complete' data (i.e. on time span that excludes the current one), specify the `--complete` flag.

```
octoviz run --complete org_name/repo_name
```

This will create a graph that omits the most recent week (if aggregating by week) or month (if aggregating by month).

By default, OctoViz will provide you with a line graph showing the time it takes for the 25th, 50th, and 90th percentile PRs to be closed. This means that, respectively, it displays the amount of time at which 25%, 50%, and 90% of PRs at that span took to be closed. If these percentiles do not work for your team, you may specify your own with the `-p` argument. If you were wanting to include lines for the 20th, 40th, 60th, and 80th percentile PR, for example, you would do so as such:

```
octoviz run -p 20,40,60,80 org_name/repo_name
```

You may include as many lines as are necessary for you and your team. Keep in mind as well that by clicking on the line in the legend, you will toggle the visibility for that line. This may be useful when wanting to hone in on one specific percentile without having to re-render the graph.


### *Putting it all together – Combined Examples*

Say you have an organization named my_org and repositories first_repo and second_repo and you wanted to:

See the data for PRs since the creation of first_repo, grouped by the month the PRs were opened, ignoring the current month, and save that to a file called 'first_repo_monthly_history.html'

```
octoviz run --no-limit -m --group-by created --complete -n first_repo_monthly_history my_org/first_repo
```

Look at the data for the last six months of first_repo and second_repo, without overriding the currently cached data, making sure that the graphs will always be showing the same time span

```
octoviz run --limit-by-months 6 --no-cache -x my_org/first_repo my_org/second_repo
```




------------------------


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
octoviz run --cleanup org_name/repo_name
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

Limit how much data to be polled from Github to only PRs created in the last 6 weeks
```
octoviz run --limit-by-weeks 6 org_name/repo_name
```

Limit how much data to be polled from Github to only PRs created in the last 6 months
```
octoviz run --limit-by-months 6 org_name/repo_name
```

Poll the data for a repository for all closed PRs
```
octoviz run --no-limit org_name/repo_name
```

Poll the full-form of the PR data
```
octoviz run --full org_name/repo_name
```

> *NOTE*: All commands below require data to be polled or cached in full-form

View pull request data by total number of lines changed in a pull request
```
octoviz run --analyze-by total org_name/repo_name
```

View data by total number of lines changed, comparing the last quarter with the one before it
```
octoviz run --analyze-by total --compare-last quarter org_name/repo_name
```

View data by total number of lines changed, comparing the current quarter with the one before it
```
octoviz run --analyze-by total --compare-current quarter org_name/repo_name
```

Group PR line data size by spans of 40 instead of the default 20
```
octoviz run --analyze-by total --round-to 40 org_name/repo_name
```
