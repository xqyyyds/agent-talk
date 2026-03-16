// uno.config.ts
import { defineConfig, presetIcons, presetWind3, transformerDirectives } from 'unocss'

export default defineConfig({
  presets: [
    presetWind3(),
    presetIcons(
      {
        extraProperties: {
          'display': 'inline-block',
          'vertical-align': 'middle',
        },
      },
    ),
  ],
  transformers: [
    transformerDirectives(),
  ],
})
