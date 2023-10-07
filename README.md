# Memtester diagnostic

[Memtester](https://linux.die.net/man/8/memtester) is a Linux utility that tests RAM.
This repo contains Python scripts that turns `memtester` into an OCP-compliant diagnostic by parsing its output using [SLY](https://sly.readthedocs.io/en/latest/), a Python implementation of [Lex](https://en.wikipedia.org/wiki/Lex_(software)) and [Yacc](https://en.wikipedia.org/wiki/Yacc). The parsing process happens in runtime, allowing the diag to report partial results while the memory test is still running.

## Basic usage
1. Install `memtester` on your DUT. Make sure the version you have is [supported]().
2. Install all the dependencies specified in `requirements.txt`.
3. Run the diag with parameters required for your use case.

For Debian-based operating systems the procedure above may look as follows:
```
apt install memtester
git clone https://github.com/opencomputeproject/ocp-diag-memtester.git
cd ocp-diag-memtester
pip install -r requirements.txt
python3 main.py --mt_args="100M 3"
```

In the last command, `mt_args` specifies arguments that the diag will pass to `memtester`.
The value above will make `memtester` reserve 100 Megabytes of RAM and test it three times.
For more info on the parameters you can pass to `memtester` run `man memtester`.

## Supported vesrions
The output `memtester` produces may vary significantly across different versions. This means that it is hard to write a parser that works properly with all of them. Thus, only a few versions are currently supported:

| Version of memtester | Status |
|-|-|
| 4.6.0 | Full support. No known issues. |
| 4.5.0 | Full support. No known issues. |
| 4.5.1 | Full support. No known issues. |
| 4.4.0 | Memtester reports memory errors for a normally working system. Error messages appear in unexpected places. No plans to support this version. |
| 4.3.0 and earlier | Source code does not compile. No plans to support this version(s). |

## Running custom `memtester`
It is possible to run this diag with a custom version of `memtester`. To do that, install your custom `memtester` in the location
of your choice and pass this location to the diag as follows (the path must include the name of the executable):

`python3 main.py --mt_args="100M 3" --mt_path="/my/favorite/location/memtester"`

In order for this diag to work properly, the output format of your `memtester` must comply with
one of the supported versions.

## Testing older memtester versions using Docker
If you need to test this diag with an older memtester version, you can use `Dockerfile` from the root directory of this repo.
This `Dockerfile` takes care of all necessary dependencies for the diag. In addition to that, it downloads `memtester` of the required version from its author's website and builds it. You can use the following command to build and run the container:

`sudo docker build -t ocp_memtester --build-arg="MT_VERSION=<version>" . && sudo docker run --rm ocp_memtester`

In the command above, replace `<version>` with the version of `memtester` you want to test. For example:

`sudo docker build -t ocp_memtester --build-arg="MT_VERSION=4.5.1" . && sudo docker run --rm ocp_memtester`

The list of available `memtester` versions is available on [this page](https://pyropus.ca./software/memtester/old-versions).

Since there is no Python parser for OCP-compliant output yet, the container does not do automatic
diag validation, so you have to manually confirm whether the version you chose works correctly.

