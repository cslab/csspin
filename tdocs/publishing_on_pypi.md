# Publishing Spin on PyPI

Wir wollen Spin und einen Satz von Plugins auf PyPI veröffentlichen,
weil wir damit den Benutzern von PaaS und DevOps-Services eine
deutlich bessere DevEx bieten können.

## Planung und Prüfung

- [x] Den Satz der Pakete festlegen, den wir veröffentlichen wollen:
  1. cs.spin: ja (Name verfügbar)
  2. spin_ce: ja
  3. spin_workflows: ja (neu)
  4. spin_frontend: ja
  5. spin_java: ja
  6. spin_python: ja

- [x] Die Working Copy auf das Vorhandensein der Secrets prüfen

  Habe das gesamte Repo (und nicht nur die working copy)
  mit `gitleaks` geprüft: nein, da ist nix.

- [x] Pypi.org-Guideline studieren

  Aufgefallen ist das
  [Trusted-Publishers-Thema](https://docs.pypi.org/trusted-publishers/).
  Damit bekommt man ein "verified"-Badge für einige Metadaten
  des Projekts. Gucken wir mal, was wir hier hinbekommen.

- [x] Auf Namenskollisionen prüfen
  1. cs.spin: nein
  2. spin_ce: nein
  3. spin_conpod: name wird eher anders
  4. spin_frontend: nein
  5. spin_java: nein
  6. spin_python: nein

- [x] Schauen, was unsere Competition on PyPI veröffentlicht.
  - https://pypi.org/project/tcsoa/: Teamcenter something
  - Placeholder package 'siemens' (WTF?)

  Nix Aufregendes

- [x] Festlegen, welche Lizenz wir nehmen wollen.

  _Q_: Wir wollen keinen Zugriff auf das Source-Code Repo von aussen
  gewähren, würden aber gerne unter einer Standard-, OSI-approved
  Lizenz veröffentlichen. Können wir das?

  _A_: Ja. Die Python-Quellen sind ja in den Wheels bereits drin. Das
  ist für die meisten interessanten Lizenzen wie MIT, BSD
  etc. hinreichend. Die Projekte auf GitHub/cslab verwenden bereits
  MIT und BSD 3-Clause. Ich tendiere gerade zu Apache License 2.0,
  weil:
  - Empfohlen von [https://choosealicense.com](https://choosealicense.com)
  - Hat den IMO den richtigen [Feature-Set](https://choosealicense.com/appendix/).

  **Note:** In den Quellen muss aber das "All rights reserved" raus.

- [x] Feststellen, ob wir Policies fürs Open-Sourcing oder
      Veröffentlichung on PyPI haben.

  Das Cloud Applications lädt schon ein paar Pakete hoch. Mit Julian
  gesprochen: er kennt keine Policy. Ich nehme an, wir haben noch
  keine. Wäre dann der Job von PTM.

- [x] Haben wir weitere Internas in dem Code/Konfiguration/
      Medataten, die wir nicht veröffentlichen wollen?

  Haben wir. Im Detail:
  1.  Die Metadaten in `pyproject.toml` beinhalten einige interne URLs
      (fixed).
  2.  Das `Readme.md`, welches wir für das Füllen von `long_description`
      nutzen wollen, beinhaltet noch interne Prozeduren (fixed).
  3.  Die Doku verweist auf viele interne Ressourcen
      (to be fixed, is not blocking though).

  Zudem haben wir Zugriffe und nicht-öffentliche Ressourcen in den
  Plugins und weiteres. Änderungsbedarf, AFAICS:
  1.  spin_ce:
      - ce_services:
        - Der HiveMQ service lädt was von einer internen URL runter (code.contact.de)
        - braucht das Tool ce_services

      - pkgtest: braucht ein internes Tool pkgtest. Ebenso hochladen? Oder Lücke lassen?
      - ce-support-tools: dito
      - localization: dito

  2.  cs.spin-conpod:
      - Hier kommen POD-spezifische Defaults rein
      - Die Workflows wandern ins cs.spin-workflows

- [x] Wie kommt die Doku zu den externen Benutzern?

  Durch den Kundenportal und -- für interne Nutzer --
  das [docs.contact.de](https://docs.contact.de).
  Blockt das initiale Hochladen aber nicht: wir wollen die PaaS Leute
  hierdurch nicht aufhalten.

- [x] Müssen wir dann noch die bereits auf PyPI veröffentlichten
      Sachen auf ConPI redundant veröffentlichen?

  Guess not. Ware seltsam, wenns anders wäre. Für den Übergang
  müssten wir aber sicherstellen, dass spin-Installation immer noch
  mit den alten URLs geht.

- [x] Haben wir einen wiederverwendbaren Account auf PyPI?

  Haben wir wohl nicht.

- [x] Neben "Trusted Publishing" gibt es noch [Digital
      Attestations](https://docs.pypi.org/attestations/). Was wollen
      wir damit machen?

  Wenn wirs hinbekommen, auf unserer self-managed GitLab-Instanz,
  dann wäre es ein Gewinn. Ist aber keine Voraussetzung für
  die initiale Bereitstellung.

- [x] We've got a naming clash with a package spin on PyPI, which is
      actively developed and used by the scientific community and is
      also a task runner :(. How do we want to deal with that?

  The naming-clash is two-fold. For one there is a
  [Python package named "spin"](https://pypi.org/project/spin/)
  For the other, this package also uses the Python namespace "spin".

  As for the first, we simply change the package name to "csspin" and
  are done. The "c" stands for CONTACT. You can think of it as the
  "CONTACTs implementation of spin", quite the same way as "CPython"
  stands for the "C-based implementation of Python".

  The "thing" itself (i.e. the taskrunner core, the whole framework
  together with the plugins, ...) should be called _spin_. We'll call
  it 'spin' in the documentation, except for a couple places where we
  explicitly mean the package name.

  The plugin packages will also be renamed as follows:
  - spin_python -> csspin_python
  - spin_ce -> csspin_ce
  - spin_java -> csspin_java
  - spin_workflows -> csspin_workflows
  - spin_vcs -> csspin_vcs
    ...

  Again: the executable script remains 'spin' for the sake of a good typing
  experience and efficiency. And we're accepting that the numpy people
  are using a different thing under the same name. It doesnt result in
  real problems for anybody, I guess.

  The namespace will also be renamed to "csspin". That way we
  [dont entrude into the namespace](https://peps.python.org/pep-0423/#respect-ownership)
  of the scientific guys w/o invitation. As a consequence, all imports
  have to be adjusted, but thats trivial work.

  [Another, rejected approach can be found below].

  The whole renaming should be done such that is causes as little
  friction as possible. Herefore, we should offer the people a time
  window to adjust the packages before removing the old wheels.

  So, things to rename (summary):
  1. Package name -> MUST csspin
  2. Python namespace name -> SHOULD csspin

  Following things will be _not_ renamed:
  1. The executable script "spin"
  2. The root of the property tree: "spin."
  3. Umgebungsvariablen usw. "SPIN\_..."
  4. The configuration directory ".spin"
  5. Most important: the taskrunner itself in its entirety -- the
     concept -- remains "spin"
  6. The source code repositories?

  This all _does lead_ to some inconsistency in naming, but one which
  also leads to _significant gains_ and one that _can be handled_ by
  anybody willing.

- [x] How to we wanna handle this renaming logistically, what do we have
      to consider.

  It should be better frictionless and with low migration efforts for
  everybody. To do that:
  - First, we will validate the whole thing our own repos. We will leave
    the old packages alone and build-up a parallel set of renamed things
    next to them. For that we will:
    - Rename according to the concept on feature branches of the
      according repos
    - Build and upload the packages to `packages-qa.contact.de`
    - Make the CI pipelines work
    - ...

  - There will be a time window, in which the packages can be mirge

- [x] Wie wollen wir auf PyPI auftreten und welche Account-Art wollen
      wir nutzen?

  Wir wollen einen gemeinsamen PyPI-Account anlegen, der für die
  Veröffentlichungen auf PyPI zu benutzen ist. Vorteil hierbei:
  - Geringere Org-Aufwände
  - Kontinuität / Einheitlichkeit
  - Übersicht über alle von uns hochgeladenen Pakete: diese
    sind nämlich in PyPI dann diesem Account zugeordnet

  Andere Organisationen benutzen auch solche Corporate Accounts, z.B.:
  - [aws](https://pypi.org/user/aws/)
  - [microsoft](https://pypi.org/user/microsoft/)

  Weitere Details:
  - Als primäre E-Mail-Adresse wollen wir unseren Team-Mailverteiler
    `qm@contact-software.com` (den wir bald umbenennen zu ptm@).
    Grund: darüber werden technische Information verteilt, welche nur
    für die Maintainer des Accounts relevant sind. Wir leiten dann
    ggf. weiter.

  - Den Account administrieren wir (PTM). Credentials gehören ebenso uns.
    Um anderen Uploads zu ermöglichen stellen wir auf Anfrage pro
    Projekt Tokens aus.

  - Ansonsten:
    - Username: contact (ist noch nicht belegt)
    - Full-Name: CONTACT Software GmbH
    - CONTACT Logo als Profilbild
    - usw.

## Der Plan

Im folgenden ein Plan, wie wir zum Ziel kommen, ohne zu viel Porzellan
zu zerschlagen. Die Ordnung der Schritte ist partiell.

1. Auf den Feature-Branches von den Repos weiter ausprobieren und
   gucken, was man so alles ändern muss
   (https://code.contact.de/qs/spin/cs.spin/-/merge_requests/145).

2. Wir passen die import statements in den Plugins an, sodass sie mit
   beiden spin core Varianten kompatibel sind, und zwar so:

   ```
   try:
        from csspin import ...
   except ImportError:
        from spin import ...
   ```

   Anschliessend machen wir Minor-Releases von jedem Package. Diese
   Releases landen automatisch bei jedem, der cs.template-like-Setups
   benutzt, weil wir auf kompatible Releases pinnen.

3. Wir sagen Torben Bescheid, dass da eine Änderung kommt
   (im Kontext eines MRs gegen cs.platform).

4. Einen gemeinsamen PyPI-Account anlegen, der für die
   Veröffentlichungen auf PyPI zu benutzen ist.

5. Das Hochladen auf test.pypi.org üben und sicherstellen, dass
   alles gut ist.

6. Wir stellen die Plugin Packages um und veröffentlichen sie auf
   pypi.org.

7. Nachdem das alles durch ist, können wir ein angepasstes spin core,
   mit dem neuen Packagenamen und einem geänderten Python Namespace,
   freigeben und überall provisionieren, ohne dass uns alles
   zusammenbricht. Hiermit hängen folgende Aktivitäten zusammen:
   1. spin.index_url auf code.contact.de instanzweit via
      CI/CD-Variablen setzen
   2. Neues spin core im cetest image bereitstellen,
   3. Neues spin core auf gitlab-ci-xy-Maschinen bereitstellen
   4. Neues cs.template release, wo die angepassten spinfiles und alle
      sonstigen damit verbundenen Änderungen abgeguckt werden
      können.

   Natürlich kündigen wir das auch an, weil:
   - man danach eine Anpassung der lokalen Konfiguration braucht und
     zwar das 'spin.index_url'-Setting, sodass interne plugins von
     packages.contact.de gezogen werden können.
   - man ab dem Zeitpunkt das spinfile.yaml umstellen kann
     (und innerhalb eines best. Zeitfensters MUSS).

8. Die beim Open-Sourcing gewonnenen Erfahrungen in eine Policy
   "giessen".

9. Irgendwann (nach ~ 1 Monat) bauen wir die
   Kompatibilietätsänderungen wieder aus.

## Rejected but to funny to throw away ;)

- [ ] We've got a naming clash with a package spin on PyPI, which is
      actively developed and used by the scientific community and is
      also a task runner :(. How do we want to deal with that?

  **Variant 2: The funky one**

  We can get less boring and more funky and rename more ;). To support
  the feeling of "German-made-PLM" (a message we use the marketing),
  we can rename the whole stuff to 'mach' (i.e. German for 'do').

  Package names would be:
  - mach[^1]
  - mach-python
  - mach-ce
  - mach-java
  - mach-frontend
  - mach-workflows

  The executable script would be 'mach'. This is very typing friendly
  (actually even a bit more than spin), supposed to transport a
  'Hanseatic feeling', makes for fun at work (which is part of the
  Python culture):

  ```
  mach provision
  mach test
  mach build
  ```

  The icing on the cake would be also renaming the built-in 'run' into
  'mal', which yields (e.g.) in:

  ```
  mach mal cdbpkg sync
  ```

  Not sure whether is feels too sloppy for the 'suits', though.

  Derived stuff (like the Python namespace etc.) would be 'mach', too.

  [^1]:
      Disclaimer: there _is_ a package on PyPI which is called
      `mach`, it is abandoned, though. Apparently, its a task runner used
      internally in Mozilla Firefox development, the authors apparently
      lost the interest in publishing it in pypi.org, though (last release
      is from 2019). We would ask the owners to transfer us the name if
      the whole idea 'flies'. If the name transfer doesnt work, we still
      could call the package 'machmal'.
