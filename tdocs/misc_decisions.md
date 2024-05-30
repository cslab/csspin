# Contains Miscellaneous Spin-Related Technical Decisions

## 1. Data Normalization / Sanity-Checks

Data normalization/sanitizing belongs close to the input channels
and should _not_ -- quite obviously -- be scattered across the
whole code. What are our input channels?

- projects `spinfile.yaml`
- users `global.yaml`
- Command line property parameters via CL (`-p <prop>`)
- `SPIN_ENV_PROP_bla` environment variables (in the future, probably)

For these "channels", we:

- Implement sanity checks in the descriptor classes in
  `schema.py`. These know the data type and ensure that an integer
  value has been passed for a property with the type int etc. The
  paths have to be normalized here.

- Note:

  1.  Property trees may contain callables. This is currently the case
      e.g. for the mkinstance plugin. These are to be evaluated in the configure-hook,
      which leads to better DevEx as we see the resulting values in
      `spin debug`.
  2.  The tree may contain objects of type "internal": those are
      undocumented, used by the implementation and have to ignored
      in this context. If general, such usages should be avoided:
      for passing around an object in the same module a global
      object should be in in most cases the better choice.

To further ease the usage of the property tree,

Another "input channel" are environment-vars and the CLI arguments, which
we read the code, both in the core and in the plugins. In this
situation, the respective code is then responsible for the sanity
checks / normalization etc.

The plugins can of course also have any other input sources. Here applies
the same logic as above: the plugins are responsible for the necessary
normalization/sanitizing of the inputs.

## 2. Which string interpolation to use in which situations?

- Situation 1:

  ```
  def bla(cfg, ...):
      info("lala {python.interpreter}")
  ```

  - more complex than the f-string interpolation
  - needs spin knowledge
  - can handle nested interpolation

  Alternatively, in the variant below:

  ```
  def bla(cfg, ...):
      info(f"lala {cfg.python.interpreter}")
  ```

  - the f-string are simpler and commonly known
  - doesn't avoid the call of `interpolation` though
  - can handle nested interpolation due to the mentions interpolation call

- Situation 2:

  ```
  def blub(...):
      info("lala {python.interpreter}")
  ```

  Here, we have no other choice, as we don't have the access to the
  ConfigTree-object

## 3. Whats the value of having Path-objects in the ConfigTree-object instead of strings, anyway?

We could use the type knowledge from the schemas to do the input
validation and path normalizing but put resulting strings into the
tree in the end. All other things being equal, this would be the
better choice, because of lower complexity.

Things aren't equal though; we have the benefit of directly using the
Path-Methods like:

```
{spin.cache} / dir / file
```

instead of

```
Path({cfg.python.interpreter}) / dir / file
```

That isn't a big benefit however; and we might revise this decision on
further findings.
