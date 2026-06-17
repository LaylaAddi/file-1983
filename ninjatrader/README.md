# VolumeProfilePro — NinjaTrader 8 Indicator

A colorful, configurable Volume Profile for NinjaTrader 8 (NinjaScript / C#).

## Features

- **Range modes**: per-session profile, or a fixed lookback bar count
- **Source**: volume-based or tick-count-based row weighting
- **Gradient shading**: low → mid → high volume rows blend across three customizable colors (default: midnight blue → spring green → orange-red)
- **Point of Control (POC)** line per session
- **Value Area** (configurable %, default 70%) high/low lines, with value-area rows tinted
- **Naked / unfilled POC** tracking — highlights POCs from prior sessions that haven't been revisited, drawn as a dashed line extending across the chart
- **Row labels** showing volume and percent-of-total per row
- **Adjustable row height** (in ticks), **profile width** (% of session width), **opacity**, and **max sessions shown**
- Every color (low/mid/high volume, POC, value area, naked POC, labels) is independently configurable in the indicator's Colors tab

## Installation

1. Open NinjaTrader 8.
2. Go to **Tools → Edit NinjaScript → Indicator...** (or right-click in the NinjaScript Editor) and create a new indicator named `VolumeProfilePro`, then replace the generated code with the contents of `VolumeProfilePro.cs`.
   - Alternatively, copy `VolumeProfilePro.cs` directly into your NinjaTrader 8 `bin\Custom\Indicators` folder and compile via **Tools → Edit NinjaScript → Compile** (F5 inside the editor).
3. Restart/compile NinjaScript (F5 in the editor).
4. On any chart, right-click → **Indicators...** → add **VolumeProfilePro**.
5. Configure under three tabs:
   - **Profile Settings**: source (Volume/TickCount), range mode (Session/FixedLookbackBars), lookback bars, row height in ticks, value area %.
   - **Display**: profile width %, max sessions shown, opacity, toggle POC/Value Area/Naked POC/Labels.
   - **Colors**: low/mid/high volume gradient stops, POC color, value area color, naked POC color, label color.

## Notes

- Designed for intraday charts; on session range mode it resets at `Bars.IsFirstBarOfSession`.
- Row height should be a multiple of the instrument's tick size — increase it on lower-priced or high-tick-count instruments to reduce row count and improve render performance.
- Naked POC detection compares each session's POC price against the price range of all later sessions' rows.
