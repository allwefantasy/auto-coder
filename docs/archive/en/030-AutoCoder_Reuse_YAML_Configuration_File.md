# 030-AutoCoder_Reuse YAML Configuration Files

When developing a requirement, we may split it into multiple YAML files (each YAML corresponds to a small iteration), and in most cases, we only need to change a few parameters such as query.

AutoCoder provides an `include_file` field in the YAML configuration file, allowing you to reuse other YAML configuration files.

For example, if I have some common configurations in the `./actions/common/remote.yml` file, and then I create a new `041_new_feature.yml` file, I can write in the `041_new_feature.yml` file like this:

```yaml
include_file: 
   - ./common/remote.yml

query: |   
   When AutoCoder detects the include_file parameter (which specifies the paths of the files to include, supporting YAML array format), it automatically loads this parameter and merges it into the args. Note that there may be recursive scenarios, with a maximum recursion depth of 10.
```

The include_file supports array format, allowing you to specify multiple files, which AutoCoder will load in the order of the array.