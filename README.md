# __name__

__name__ is an ultra minimalist static site generator with powerful templating possibilities.

## Requirements

__name__ is a python program, it runs on gnu/linux systems and requires the following libraries to work:

```
python3
python3-markdown
python3-bs4
python3-yaml
python3-pil
python3-inotify
rsync
```

## Usage

```
python3 -m __name__ [-h] [--src SRC] [--out OUT] [--watch] [--version]

options:
  -h, --help  show this help message and exit
  --src SRC   site sources directory (default: ./src)
  --out OUT   site build output directory (default: ./build)
  --watch     watch for changes in sources and rebuild automatically (default: False)
  --version   show program's version number and exit

```

## Templating syntax

**Single line syntax**

```
{% CODE %}
```

Will be replaced by the return value of `CODE`, interpreted as python code.

**Multiline syntax**

```
{%%
    CODE
%%}
```

Will be replaced by the standard output of `CODE`'s execution' (fed with `print()`).

## Templating functions
