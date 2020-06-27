#!/usr/bin/python3

import argparse
import glob
import json
import os
import re
import shlex
import subprocess



toolsDirPath = os.path.dirname(os.path.abspath(__file__))
ltexPath = os.path.abspath(os.path.join(toolsDirPath, ".."))



def removeKeyIfPresent(d, key):
  if key in d: del d[key]



def run(cmd, **kwargs):
  print("Running {}...".format(" ".join(shlex.quote(x) for x in cmd)))
  return subprocess.run(cmd, stdout=subprocess.PIPE, cwd=toolsDirPath)

def fetchLanguages(toolsDirPath, ltexLsPath):
  classPath = os.pathsep.join([toolsDirPath, os.path.join(ltexLsPath, "lib", "*")])
  run(["javac", "-cp", classPath, "LanguageToolLanguageLister.java"])
  process = run(["java", "-cp", classPath, "LanguageToolLanguageLister"])
  stdout = process.stdout.decode()
  languages = sorted([dict(zip(("languageShortCode", "languageName"), line.split(";")))
      for line in stdout.splitlines()], key=lambda x: x["languageShortCode"])
  ltLanguageShortCodes = [x["languageShortCode"] for x in languages]
  ltLanguageNames = [x["languageName"] for x in languages]
  return ltLanguageShortCodes, ltLanguageNames



def updatePackageJson(ltLanguageShortCodes, ltLanguageNames):
  packageJsonPath = os.path.join(ltexPath, "package.json")
  with open(packageJsonPath, "r") as f: packageJson = json.load(f)
  settings = packageJson["contributes"]["configuration"]["properties"]

  settings["ltex.language"]["enum"] = ltLanguageShortCodes
  settings["ltex.language"]["enumDescriptions"] = [
      "%ltex.i18n.configuration.ltex.language.{}.enumDescription%".format(x)
      for x in ltLanguageShortCodes]

  removeKeyIfPresent(settings["ltex.dictionary"], "propertyNames")
  settings["ltex.dictionary"]["properties"] = {
        languageShortCode: {
          "type": "array",
          "items": {
            "type": "string",
          },
          "markdownDescription": "%ltex.i18n.configuration.ltex.dictionary."
            "{}.markdownDescription%".format(languageShortCode),
          "description": "%ltex.i18n.configuration.ltex.dictionary."
            "{}.description%".format(languageShortCode),
        }
        for languageShortCode, languageName in zip(ltLanguageShortCodes, ltLanguageNames)
      }

  removeKeyIfPresent(settings["ltex.disabledRules"], "propertyNames")
  settings["ltex.disabledRules"]["properties"] = {
        languageShortCode: {
          "type": "array",
          "items": {
            "type": "string",
          },
          "markdownDescription": "%ltex.i18n.configuration.ltex.disabledRules."
            "{}.markdownDescription%".format(languageShortCode),
          "description": "%ltex.i18n.configuration.ltex.disabledRules."
            "{}.description%".format(languageShortCode),
        }
        for languageShortCode, languageName in zip(ltLanguageShortCodes, ltLanguageNames)
      }

  removeKeyIfPresent(settings["ltex.enabledRules"], "propertyNames")
  settings["ltex.enabledRules"]["properties"] = {
        languageShortCode: {
          "type": "array",
          "items": {
            "type": "string",
          },
          "markdownDescription": "%ltex.i18n.configuration.ltex.enabledRules."
            "{}.markdownDescription%".format(languageShortCode),
          "description": "%ltex.i18n.configuration.ltex.enabledRules."
            "{}.description%".format(languageShortCode),
        }
        for languageShortCode, languageName in zip(ltLanguageShortCodes, ltLanguageNames)
      }

  for settingName in list(settings.keys()):
    if (re.match("^ltex\.languageSettings\.", settingName) or
          re.match("^ltex\.([^\.]+)\.(dictionary|enabledRules|disabledRules)", settingName)):
      del settings[settingName]

  for languageShortCode, languageName in zip(ltLanguageShortCodes, ltLanguageNames):
    for settingSubName in ["dictionary", "enabledRules", "disabledRules"]:
      metaVariable = ("WORD" if settingSubName == "dictionary" else "RULE")
      settings["ltex.{}.{}".format(languageShortCode, settingSubName)] = {
            "type": "array",
            "scope": "resource",
            "default": [],
            "markdownDeprecationMessage": "**Deprecated:** This setting has been renamed. Use "
                "`\"ltex.{0}\": {{\"{1}\": [\"<{2}1>\", \"<{2}2>\", ...]}}` instead.".format(
                  settingSubName, languageShortCode, metaVariable),
            "deprecationMessage": "Deprecated: This setting has been renamed. Use "
                "'\"ltex.{0}\": {{\"{1}\": [\"<{2}1>\", \"<{2}2>\", ...]}}' instead.".format(
                  settingSubName, languageShortCode, metaVariable),
          }

  with open(packageJsonPath, "w") as f:
    json.dump(packageJson, f, indent=2, ensure_ascii=False)
    f.write("\n")

def updatePackageI18nJson(ltLanguageShortCodes, ltLanguageNames, uiLanguage):
  packageI18nJsonPath = (os.path.join(ltexPath, "package.nls.json") if uiLanguage == "eng" else
      os.path.join(ltexPath, "i18n", uiLanguage, "package.i18n.json"))
  with open(packageI18nJsonPath, "r") as f: oldPackageI18nJson = json.load(f)

  newPackageI18nJson = {}

  for key, value in oldPackageI18nJson.items():
    newPackageI18nJson[key] = value

    if key == "ltex.i18n.configuration.ltex.language.description":
      for ltLanguageShortCode, ltLanguageName in zip(ltLanguageShortCodes, ltLanguageNames):
        prefix = f"ltex.i18n.configuration.ltex.language.{ltLanguageShortCode}"
        newPackageI18nJson[f"{prefix}.enumDescription"] = ltLanguageName

    elif re.match(r"^ltex\.configuration\.ltex\.language\..+\.", key) is not None:
      continue

    elif key == "ltex.i18n.configuration.ltex.dictionary.description":
      for ltLanguageShortCode, ltLanguageName in zip(ltLanguageShortCodes, ltLanguageNames):
        prefix = f"ltex.i18n.configuration.ltex.dictionary.{ltLanguageShortCode}"

        if uiLanguage == "deu":
          newPackageI18nJson[f"{prefix}.markdownDescription"] = (
              "Liste von zusätzlichen Wörtern der Sprache "
              f"`{ltLanguageShortCode}` ({ltLanguageName}), die nicht als Schreibfehler "
              "gewertet werden sollen.")
          newPackageI18nJson[f"{prefix}.description"] = (
              "Liste von zusätzlichen Wörtern der Sprache "
              f"'{ltLanguageShortCode}' ({ltLanguageName}), die nicht als Schreibfehler "
              "gewertet werden sollen.")
        else:
          newPackageI18nJson[f"{prefix}.markdownDescription"] = (
              f"List of additional `{ltLanguageShortCode}` ({ltLanguageName}) words that should "
              "not be counted as spelling errors.")
          newPackageI18nJson[f"{prefix}.description"] = (
              f"List of additional '{ltLanguageShortCode}' ({ltLanguageName}) words that should "
              "not be counted as spelling errors.")

    elif re.match(r"^ltex\.configuration\.ltex\.dictionary\..+\.", key) is not None:
      continue

    elif key == "ltex.i18n.configuration.ltex.disabledRules.description":
      for ltLanguageShortCode, ltLanguageName in zip(ltLanguageShortCodes, ltLanguageNames):
        prefix = f"ltex.i18n.configuration.ltex.disabledRules.{ltLanguageShortCode}"

        if uiLanguage == "deu":
          newPackageI18nJson[f"{prefix}.markdownDescription"] = (
              "Liste von zusätzlichen Regeln der Sprache "
              f"`{ltLanguageShortCode}` ({ltLanguageName}), die deaktiviert werden sollen "
              "(falls standardmäßig durch LanguageTool aktiviert).")
          newPackageI18nJson[f"{prefix}.description"] = (
              "Liste von zusätzlichen Regeln der Sprache "
              f"'{ltLanguageShortCode}' ({ltLanguageName}), die deaktiviert werden sollen "
              "(falls standardmäßig durch LanguageTool aktiviert).")
        else:
          newPackageI18nJson[f"{prefix}.markdownDescription"] = (
              f"List of additional `{ltLanguageShortCode}` ({ltLanguageName}) rules that should "
              "be disabled (if enabled by default by LanguageTool).")
          newPackageI18nJson[f"{prefix}.description"] = (
              f"List of additional '{ltLanguageShortCode}' ({ltLanguageName}) rules that should "
              "be disabled (if enabled by default by LanguageTool).")

    elif re.match(r"^ltex\.configuration\.ltex\.disabledRules\..+\.", key) is not None:
      continue

    elif key == "ltex.i18n.configuration.ltex.enabledRules.description":
      for ltLanguageShortCode, ltLanguageName in zip(ltLanguageShortCodes, ltLanguageNames):
        prefix = f"ltex.i18n.configuration.ltex.enabledRules.{ltLanguageShortCode}"

        if uiLanguage == "deu":
          newPackageI18nJson[f"{prefix}.markdownDescription"] = (
              "Liste von zusätzlichen Regeln der Sprache "
              f"`{ltLanguageShortCode}` ({ltLanguageName}), die aktiviert werden sollen "
              "(falls standardmäßig durch LanguageTool deaktiviert).")
          newPackageI18nJson[f"{prefix}.description"] = (
              "Liste von zusätzlichen Regeln der Sprache "
              f"'{ltLanguageShortCode}' ({ltLanguageName}), die aktiviert werden sollen "
              "(falls standardmäßig durch LanguageTool deaktiviert).")
        else:
          newPackageI18nJson[f"{prefix}.markdownDescription"] = (
              f"List of additional `{ltLanguageShortCode}` ({ltLanguageName}) rules that should "
              "be enabled (if disabled by default by LanguageTool).")
          newPackageI18nJson[f"{prefix}.description"] = (
              f"List of additional '{ltLanguageShortCode}' ({ltLanguageName}) rules that should "
              "be enabled (if disabled by default by LanguageTool).")

    elif re.match(r"^ltex\.configuration\.ltex\.enabledRules\..+\.", key) is not None:
      continue

  with open(packageI18nJsonPath, "w") as f:
    json.dump(newPackageI18nJson, f, indent=2, ensure_ascii=False)
    f.write("\n")



def main():
  parser = argparse.ArgumentParser(description="Fetches all supported language codes from "
      "LanguageTool and updates the language-specific parts of package.json accordingly")
  parser.add_argument("--ltex-ls-path", default="lib/ltex-ls-*",
      help="path to ltex-ls relative from the root directory of LTeX, supports wildcards")
  args = parser.parse_args()

  ltexLsPaths = glob.glob(os.path.join(ltexPath, args.ltex_ls_path))
  assert len(ltexLsPaths) > 0, "ltex-ls not found"
  assert len(ltexLsPaths) < 2, "multiple ltex-ls found via wildcard"
  ltexLsPath = ltexLsPaths[0]
  print("Using ltex-ls from {}".format(ltexLsPath))

  print("Fetching languages from LanguageTool...")
  ltLanguageShortCodes, ltLanguageNames = fetchLanguages(toolsDirPath, ltexLsPath)
  assert len(ltLanguageShortCodes) > 0, "No languages found."
  print("LanguageTool Languages: {}".format(", ".join(ltLanguageShortCodes)))

  print("Updating package.json...")
  updatePackageJson(ltLanguageShortCodes, ltLanguageNames)

  print("Updating package.nls.json...")
  updatePackageI18nJson(ltLanguageShortCodes, ltLanguageNames, "eng")

  for uiLanguage in sorted(os.listdir(os.path.join(ltexPath, "i18n"))):
    if not os.path.isdir(os.path.join(ltexPath, "i18n", uiLanguage)): continue
    print("Updating i18n/{}/package.i18n.json...".format(uiLanguage))
    updatePackageI18nJson(ltLanguageShortCodes, ltLanguageNames, uiLanguage)



if __name__ == "__main__":
  main()
