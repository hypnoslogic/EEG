# EEG for Anaesthetists

An open, referenced teaching resource for anaesthetists on reading the raw EEG, the spectrogram (DSA) and processed EEG indices (GE Entropy, BIS, Masimo SedLine).

- Built around the 2026 international Delphi learning outcomes for EEG education in anaesthesiology (Basic / Advanced).
- Structured like the Safe Brain Initiative (ESAIC) EEG boot camp.
- Core sources: Purdon et al., *Anesthesiology* 2015; Lee, Egan & Johnson, *Korean J Anesthesiol* 2021; plus trials and reviews to October 2026.
- Every EEG image is synthetic and regenerable, so no patient data is involved.

**For education only.** This is not a clinical protocol or a medical device.

## Publish on GitHub Pages

1. Create a repository and push the contents of this folder to the repository root.
2. Go to **Settings → Pages → Build and deployment**, choose **Deploy from a branch**, select `main` and `/ (root)`, then save.
3. The site appears at `https://<user>.github.io/<repo>/` after a minute or two.

The `.nojekyll` file tells GitHub Pages to serve the files as they are.

**Before publishing**, copy your `eeg_rt_spectrum.py` into `tools/`. Module 7 and the reference list link to `tools/eeg_rt_spectrum.py`.

## Updating content

```
src/pages/*.html        page content (fragments with a small header comment)
src/references.json     single reference database (APPEND new entries so numbering stays stable)
build.py                builds the *.html pages in the root (no dependencies)
tools/make_figures.py   regenerates every figure in img/ (numpy, scipy, matplotlib)
assets/                 stylesheet and the band-scheme toggle script
```

```bash
python build.py                       # rebuild pages after editing src/
pip install numpy scipy matplotlib
python tools/make_figures.py          # regenerate figures (deterministic)
```

Macros for use in fragments are documented at the top of `build.py`: `{{cite:key}}`, `{{lo:RW7}}`, `{{basic}}`, `{{adv}}`, `{{band:alpha}}`, `{{fig:…}}`, `{{sfig:…}}`. The build stops with an error on an unknown citation key or an unexpanded macro.

After an update, change the page's `reviewed:` date and add a row to the changelog in `src/pages/roadmap.html`.

## Licence

- Text and original figures: CC BY-NC-SA 4.0.
- Code: MIT is suggested (add your preferred LICENCE file).
- Third-party material is credited on `references.html` and keeps its original licence. This includes the haemodynamic table adapted from Lee et al. (CC BY-NC 4.0), the Delphi learning outcomes, and the ShARP mnemonic from the boot camp paper (CC BY 4.0).
