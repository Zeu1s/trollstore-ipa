# TrollStore IPA — a GitHub Action

Build any iOS app in GitHub Actions and get back an IPA that **TrollStore** can install
permanently. No Apple Developer account, no certificates, no provisioning profiles, and no
Mac on your desk.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Why this exists

The usual "build an IPA in CI" guides assume you have an Apple Developer account and a
`.p12` + `.mobileprovision` to feed `xcodebuild`. That is the wrong tool for a large and very
real group of iOS developers:

- people shipping **TrollStore / sideload builds** of their own apps
- **jailbreak and tweak-adjacent** tools that cannot go through the App Store
- open source iOS apps distributed straight from **GitHub Releases**
- anyone testing on their own device without paying for a developer program

Doing this by hand means rediscovering the same four failures every time: `xcodebuild` aborts
looking for a signing identity, nested Mach-O binaries get invalidated by the outer signature,
`ldid` behaves differently across Homebrew versions, and a silently broken `.ipa` only fails
once it is on the phone. This action encodes the working order once.

## What it actually does

1. Selects an Xcode version on the macOS runner.
2. Installs `ldid` (skips the install if it is already present).
3. Resolves Swift Package dependencies.
4. Archives with **every** signing step disabled — `CODE_SIGNING_ALLOWED=NO`,
   `CODE_SIGNING_REQUIRED=NO`, empty `CODE_SIGN_IDENTITY` and `DEVELOPMENT_TEAM`.
5. Reads `CFBundleExecutable` from `Info.plist` instead of guessing the binary name.
6. Signs **nested** Mach-O files first, then the main binary, so the outer signature is not
   computed over bytes that are about to change.
7. Zips a `Payload/` tree and verifies the archive with `unzip -t` before uploading.

## Usage

```yaml
name: Release
on:
  workflow_dispatch:

jobs:
  ipa:
    runs-on: macos-15
    steps:
      - uses: actions/checkout@v4
      - uses: Zeu1s/trollstore-ipa@v1
        with:
          project: MyApp.xcodeproj
          scheme: MyApp
          version: 1.0.0
          build-number: 1
          ipa-name: MyApp-trollstore.ipa
          artifact-name: myapp-ipa
```

The IPA is uploaded as an artifact called `myapp-ipa`. To attach it to a Release instead,
read the outputs:

```yaml
      - id: build
        uses: Zeu1s/trollstore-ipa@v1
        with:
          workspace: Pods/MyApp.xcworkspace
          scheme: MyApp
      - uses: softprops/action-gh-release@v2
        with:
          files: ${{ steps.build.outputs.ipa-path }}
```

## Inputs

| Input | Default | Notes |
| --- | --- | --- |
| `project` | `""` | Path to `.xcodeproj`. Mutually exclusive with `workspace`. |
| `workspace` | `""` | Path to `.xcworkspace`, e.g. when using CocoaPods. |
| `scheme` | — | **Required.** The scheme to archive. |
| `configuration` | `Release` | |
| `sdk` | `iphoneos` | |
| `xcode-version` | `latest-stable` | Passed to `maxim-lobanov/setup-xcode`. |
| `version` | `""` | Sets `MARKETING_VERSION`. Empty keeps the project value. |
| `build-number` | `""` | Sets `CURRENT_PROJECT_VERSION`. Digits only. |
| `entitlements` | `""` | Path to an entitlements plist. Empty signs with no entitlements. |
| `ipa-name` | `app.ipa` | |
| `artifact-name` | `trollstore-ipa` | Set to `""` to skip the artifact upload. |
| `extra-xcodebuild-args` | `""` | Appended verbatim to the `xcodebuild` call. |

## Outputs

| Output | Description |
| --- | --- |
| `ipa-path` | Workspace-relative path to the generated IPA. |
| `app-path` | Absolute path to the built `.app` inside the archive. |

## Entitlements

Plain `TrollStore` installs work with **no** entitlements, which is the default here. Supply
`entitlements` only if your app genuinely needs specific ones — TrollStore rejects some
platform-reserved entitlements, and adding them is the most common reason an otherwise valid
IPA fails to install.

## Requirements and limits

- A **macOS** runner (`macos-14`, `macos-15`, …). iOS builds cannot run on Linux or Windows.
- Public repositories run macOS jobs on free minutes; private ones consume them at a multiplier.
- The output is an **ad-hoc signed** IPA. It installs via TrollStore or, on a device you
  control, other sideloading paths — it will not install through the normal App Store
  pipeline, and it is not a substitute for a signed distribution build.
- iOS 15+ device support depends entirely on TrollStore's own supported firmwares.

## License

MIT — see [LICENSE](LICENSE).
