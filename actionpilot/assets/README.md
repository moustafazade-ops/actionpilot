# Local interface assets

- `ap_green.png`: original transparent ActionPilot logo supplied by Haos; embedded unchanged in all brand marks and used as the favicon.

- Tabler outline icons: `@tabler/icons` 3.49.0, https://github.com/tabler/tabler-icons (MIT, license in `icons/LICENSE`).
- Geist Sans and Mono variable fonts: `geist` 1.7.2, https://github.com/vercel/geist-font (SIL Open Font License, in `fonts/LICENSE.txt`).

Only the used SVGs and two fonts are vendored. The interface embeds these files locally; no CDN or runtime network request is required. Icon stroke width is normalized to 1.75 in the presentation helper.
