# OctoViz

A tool to visualize PR lifetime data from Github!

Before using, ensure you have a github OAuth token to use. Create profiles using `octoviz profile create` to specify the url to connect to (if in corporate environment) and the token to use.

To install, simply use `pip install .`. For usage, check `octoviz -h` for more information. A virtual environment is strongly encouraged if developing, or if there is a concern for conflicting dependencies with your system.

Cached files and generated HTML files are found in the home directory under the folder '.octoviz'. Commands are included to flush the cache, the html files, or everything, as well as to create/delete/update profiles.

Windows support is currently experimental but presumed to be complete.