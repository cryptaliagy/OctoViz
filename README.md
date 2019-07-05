# OctoViz

A tool to visualize PR lifetime data from Github!

Before using, ensure you have a github OAuth token to use.

You can set the URL (for Enterprise environments) and the token at runtime with flags or through the GITHUB_API_TOKEN and GITHUB_URL environment variables

To install, simply use `pip install .`. For usage, check `octoviz -h` for more information. A virtual environment is strongly encouraged if developing, or if there is a concern for conflicting dependencies with your system.

Cached files and generated HTML files are found in the home directory under the folder '.octoviz'. Commands are included to flush the cache, the html files, or everything.

Windows support is currently experimental but presumed to be complete.