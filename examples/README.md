# Example datasets

This directory contains small, self-contained example scenarios for the kit.

- [continuous_lora](continuous_lora) - the bundled Sobel-style measurement example used in the package README, with formula (2.7) and experimental data referenced from Dudarek and Martyniuk's pre-print on discrete-to-continuous LoRa parameter estimation.
- [household_temperature](household_temperature) - smart-home temperature, humidity, and window-state signals.
- [rainy_walkway](rainy_walkway) - wet-surface estimation under rain, glare, and wind.
- [grocery_shelf_count](grocery_shelf_count) - shelf-item counting under blur, occlusion, and low light.

Each example folder contains a `config.json` and a matching `measurements.csv` that can be used with `contrib validate` and `contrib run`.

Short notes on the AI-generated examples:

- [household_temperature](household_temperature) is AI-generated and models everyday home temperature estimation, with the formula testing how thermostat, wall sensor, humidity, window opening, and occupancy combine when a room drifts from the true temperature.
- [rainy_walkway](rainy_walkway) is AI-generated and models a wet pavement / walkway safety scenario, with the formula focusing on how wetness, rain intensity, exposure, and wind together influence the predicted surface condition.
- [grocery_shelf_count](grocery_shelf_count) is AI-generated and models a familiar store-shelf counting task, with the formula capturing how blur, occlusion, brightness, and low-light flags affect count quality.
