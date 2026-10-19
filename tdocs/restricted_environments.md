# Downloads and restricted environments

Customers run spin in networks without access to the public internet. Every
artifact that spin or a plugin fetches from a public host needs a property that
points to a different location. That property must document what spin expects to
find there.

## Rules

... that must be followed for new plugin packages. They also outline the current
gaps in our existing ones.

### 1. Download of archives, binaries, etc.

When a plugin downloads an archive, binary or jar, it provides
`<tool>.download_url`:

1. The value is the URL of a directory. The plugin appends the file name that
   it _may_ build from `<tool>.version`, the OS and the architecture, for example
   `Redis-{ce_services.redis.version}-Windows-x64-msys2.zip` (as of csspin-ce
   v5.0.0).
2. The default is the current upstream URL. For example
   `https://github.com/redis-windows/redis-windows/releases/download/{ce_services.redis.version}`
   (as of csspin-ce v5.0.0). This way users see the default sources in the
   configuration tree and can mirror the upstream layout.
3. The property help lists the file names the directory holds, the archive
   format (zip, tar.gz, tar.xz, jar) and the layout inside the archive that the
   plugin's extraction relies on. For example
   ```yaml
   # ce_services_schema.yaml
   redis:
     type: object
     properties:
       version:
         type: str
         help: The redis version to use.
       download_url:
         type: str
         help: |
           URL of a directory containing downloadable redis source archives
           as ``Redis-{ce_services.redis.version}-Windows-x64-msys2.zip``.
   ```
4. Where `<tool>.use` exists, it skips the download and takes precedence.

"Open" questions:

- What about `csspin-python.nuget` that is configured as:
  ```python
  nuget = (
      config(
          url="https://dist.nuget.org/win-x86-commandline/latest/nuget.exe",
          exe="{spin.data}/nuget.exe",
          source="https://api.nuget.org/v3/index.json",
      ),
  )
  ```
  Replacing `url` with `download_url`, `source` with a kind of `index_url`, and
  adding a `version` property pointing to `latest` would be breaking. The same
  counts for the `pyenv` property subtree. We probably have more places like
  that. If we frame this endeavor as non-breaking, we'd do nothing. For this
  case it is already configurable enough. So no alignment is needed. The same
  counts for `csspin-java.mvn` via its `mirror` and `url` properties.

Gaps we know of:

- `csspin-ce`:
  - `ce_services` basically everything
    - special case: erlang
      - we download and compile it. On air-gapped machines, we probably don't
        have compilers and such.
  - `mkinstance`: graphviz
- `csspin-tooling`: probably out of scope for now
- ...more

### 2. Installation of Python packages

Python packages for the in-process environment must be installed through
`spin.index_url` while those required in the subprocess environment need to be
installed through `python.index_url`.

Gaps we know of are:

- `csspin`'s "update check" must use `spin.index_url`
- `csspin-python`:
  - `python`'s "nuget_install" function calls stuff like `-mpip install -U pip
wheel packaging` which isn't routed through any `index_url`.

### 3. Installation of JavaScript packages

JavaScript packages must be installed through a new `node.registry_url`
property. We have two different yarn versions out there - both must work align
with that.

Gaps we know of are:

- `csspin-ce.mkinstance`:
  - `webmake devupdate`
  - Requires `sass` and `yarn` that are not routed through any `registry_url`.
    (affects `csspin-frontend.node`)
- `csspin-frontend`:
  - `node` to perform yarn installations
  - `jest` needs the (new) `registry_url` of the node plugin
  - `js_sbom` needs to use the `registry_url` as well (currently only uses the
    pip index url)

### 4. General use of indices

Any plugin that installs packages through indices must provide such. Currently,
we don't know any (except the already mentioned ones).

### 5. Mirrors

- Tools that already have `mirror[s]` keep them as an ordered fallback. Their
  `download_url` defaults to empty.
- Unlike for `download_url`, we do not define the expected format behind
  `mirror[s]`. Nothing changes here.
- Precedence: `<tool>.use`, `<tool>.download_url`, `<tool>.mirror[s]`. Setting
  all is valid.

Gaps we know of:

- `csspin-python.uv_provisioner` to install Python (subprocess environment),
  there is a `--mirror` option for `uv` we can use
- `csspin-python.python.pyenv`:
  - `python.pyenv.url` for installing pyenv already works (similar to
    `download_url`)
  - The Python interpreter installed by pyenv needs `PYTHON_BUILD_MIRROR_URL` ->
    so a new mirror property might be useful here.
- `pytest.playwright` for downloading browsers via PLAYWRIGHT_DOWNLOAD_HOST

### 6. Things I have no name for

`csspin-java.mvn` can download stuff. The only way to influence this seems to be
a `settings.xml` file. One can use the existing `mvn.opts`that allows extending
the command-line of Maven to define upstream endpoints.

## External tools

Customers configure spin properties. When a tool offers a flag or a config
file, the plugin uses it. When a tool reads only an environment variable, the
plugin sets that variable from the property with `setenv`, which echoes it in
the output. Users of spin should not influence how underlying tools work via
non-spin environment variables unless for edge case.

## Example

```python
defaults = config(
    traefik=config(
        version="2.11.2",
        download_url=(
            "https://github.com/traefik/traefik/releases/download/"
            "v{ce_services.traefik.version}"
        ),
    ),
)


def provision(cfg):
    download(f"{cfg.ce_services.traefik.download_url}/{archive}", archive_path)
```

## Misc

- `csspin.download` probably reads `file://` URLs.
- In general: we probably need more than a single sentence for most `help`
  properties in schemas. Since this is part of the documentation and also
  available locally (`spin schemadoc`) it doesn't hurt here.
- Every place not mentioned explicitly is expected to work already and might
  just need some documentation.
- `csspin-java.java` uses the `install-jdk` package which only allows to chose a
  vendor to pull the JDK from. So we either need a `download_url` or look for a
  replacement.

## Out of scope

- `csspin.download` sends no credentials, so internal hosts that require
  authentication are out of scope. Credentials in the URL (`user:secret@host`)
  do not work, only an `Authorization` header does, and no plugin passes one.
- csspin-tooling (no demand yet)
- Cypress (we no longer want to maintain this part)
- Playwright plugin (deprecated, now lives in the pytest plugin)
- `HTTP_PROXY` setting from the customer side bc we have too many places that
  are 'custom' and can't be handled by a generic HTTP endpoint
