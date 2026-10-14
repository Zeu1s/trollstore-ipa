# Contributing

## Before you open an issue

Attach the **full build log** from the failing step of the Actions run. Almost every failure in
this pipeline is an `xcodebuild` error, and the useful part is 200 lines above the last line you
can see. Redact anything secret — the workflow does not print credentials, but your own project
might.

Please include:

- the `with:` block you passed to the action
- whether the project uses a `.xcodeproj` or a `.xcworkspace`
- the runner image (`macos-14`, `macos-15`, …)
- the Xcode version selected (`xcodebuild -version`)

## How it fails

| Symptom | Likely cause |
| --- | --- |
| `No signing certificate ... found` | A signing setting is being reintroduced — check `extra-xcodebuild-args` for a `CODE_SIGN_*` override. |
| `No .app found in the archive` | The scheme builds a framework/extension, not an app target. |
| Builds fine, TrollStore refuses to install | Entitlements. Try with no `entitlements` input first, then add only what the app needs. |
| `ldid` not found | Homebrew on the runner failed to install it; re-run, or pin the formula version in a PR. |
| Install succeeds, app exits on launch | Usually a missing entitlement or an iOS version TrollStore does not support. |

## Making a change

1. Branch off `main`.
2. Edit `action.yml`.
3. Run the validator locally:

   ```bash
   pip install pyyaml
   python tools/validate_action.py
   ```

   It checks the composite-action structural rules GitHub enforces, and runs `bash -n` over
   every embedded `run:` block after substituting `${{ ... }}` expressions. It also fails on
   invalid YAML and on outputs that reference a step id which does not exist.

   CI runs the same script, so a local pass is a CI pass.
4. Open a pull request.

## Releases and versioning

Consumers pin to a **major tag** (`uses: Zeu1s/trollstore-ipa@v1`), so releases are tag-driven:

- `main` is where changes land; `@v1` does **not** move with `main`.
- A maintainer cuts a release by pushing a tag and publishing a GitHub Release with the changelog:

  ```bash
  git tag -a v1.1.0 -m "..."
  git push origin v1.1.0
  gh release create v1.1.0 --generate-notes
  git tag -f v1 v1.1.0        # move the major alias last, after the patch tag exists
  git push -f origin v1
  ```

- Breaking input or output changes go to a new major (`v2`), never into a moved `v1`.

Please do not ask for a specific commit SHA to be pinned in the README — the major tag is the
supported contract.

## Scope

This action exists to produce **TrollStore-installable** builds. It deliberately does not
handle App Store submission, provisioning profiles, paid developer certificates, or code
signing for other distribution channels. Those are different problems and adding them here
would make the failure modes much harder to reason about.
