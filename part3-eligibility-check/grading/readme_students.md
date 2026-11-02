# Part 3 eligibility check

These are the scripts the TAs run on your team repository to decide whether your Part 3 submission is eligible for grading. The rules are in the Part 3 assignment document under "Eligibility For Grading". Run the scripts yourself before the deadline. The TAs see the same output that you see.

## What you need

- Python 3.8 or later. You do not need to install any packages.
- Keep all the files of this folder together. The runner finds the other scripts in its own folder.
- On Windows, type `python` where the commands below say `python3`.

## How to run

From your team repository's root folder:

```
python3 path/to/grading/check_part3.py .
```

Or from anywhere, giving the path of the repository:

```
python3 check_part3.py path/to/your-team-repo
```

The TAs run the same command on the commit that is on your default branch at the deadline. Commit and push before you run the final check. To be sure, you can run it again on a fresh clone.

## Reading the output

- 🟢 the item passes.
- 🔴 the item fails. The line says which file and which rule.
- ⚪ the script could not check the item. This happens when the Structurizr command-line tool is not installed, hence the script cannot check that `workspace.dsl` opens in Structurizr Lite. Open it in Structurizr Lite yourself.
- The last line is the result: `ELIGIBLE for grading` or `NOT eligible` with the failure count. The exit code is the failure count, so zero means eligible.

## What each script checks

The runner, `check_part3.py`, checks nothing itself. It runs these five and adds up their failures:

| Script | Checks |
|---|---|
| `check_sdd_features_layout.py` | the `features/` folder: one folder per feature named in lowercase with hyphens, a `system` folder, a `requirements.md` in each, and IDs prefixed with the folder name |
| `check_req_form.py` | one `requirements.md` at a time: the line form `- **id-nnn** (pattern): sentence`, one requirement per line, each ID once, and the form of the `supersedes:` and `superseded by` lines |
| `check_ears.py` | one `requirements.md` at a time: the EARS wording of each sentence. The system name is written in braces, as in `the {EventHub} shall`; the sentence contains "shall", opens with the keyword of its pattern, has a comma before the system name, and the system name comes directly before "shall" |
| `check_supersedes.py` | every `supersedes:` line has a matching line at the other end: the old requirement ends with `superseded by <new-id>` and the new one carries `supersedes: <old-id>`, also across folders |
| `check_structurizr.py` | `workspace.dsl` at the root with the workspace, model, and views blocks, at least one context, container, and component view, and a PNG or SVG export per view in `diagrams/`. Write each view as a multi-line block, with the opening brace at the end of the declaration line and `include *` and the other statements on the lines below, as in the Structurizr documentation. A view written on one line is not counted |


## What the scripts do not check

They read the text only. They do not judge whether a requirement is right, complete, or well written, or whether a diagram matches your design. Passing the check only makes the submission eligible for grading. The grading is based on the content.
