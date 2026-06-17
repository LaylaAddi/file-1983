#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Windows;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// VolumeProfilePro
// A colorful, configurable session/fixed-range Volume Profile for NinjaTrader 8.
// Features:
//  - Session or fixed-bar-count lookback ranges
//  - Volume or tick-count based profile
//  - Gradient color ramp from low-volume to high-volume rows (customizable palette)
//  - Point of Control (POC), Value Area High/Low with adjustable Value Area %
//  - Naked / unfilled POC tracking across multiple sessions
//  - Optional row labels showing volume and % of total
//  - Adjustable row height (tick size multiplier), profile width, placement, and opacity

namespace NinjaTrader.NinjaScript
{
    public enum VolumeProfileSource
    {
        Volume,
        TickCount
    }

    public enum VolumeProfileRange
    {
        Session,
        FixedLookbackBars
    }
}

namespace NinjaTrader.NinjaScript.Indicators
{
    public class VolumeProfilePro : Indicator
    {
        private class ProfileRow
        {
            public double Price;
            public double Value;
        }

        private class ProfileSession
        {
            public DateTime StartTime;
            public DateTime EndTime;
            public int StartBarIdx;
            public int EndBarIdx;
            public Dictionary<double, double> Rows = new Dictionary<double, double>();
            public double Poc = double.NaN;
            public double Vah = double.NaN;
            public double Val = double.NaN;
            public bool PocFilled = true;
        }

        private List<ProfileSession> sessions = new List<ProfileSession>();
        private ProfileSession currentSession;
        private double tickSizeRows;

        private Color LowVolumeColor { get { return ((SolidColorBrush)LowVolumeColorBrush).Color; } }
        private Color MidVolumeColor { get { return ((SolidColorBrush)MidVolumeColorBrush).Color; } }
        private Color HighVolumeColor { get { return ((SolidColorBrush)HighVolumeColorBrush).Color; } }
        private Color PocColor { get { return ((SolidColorBrush)PocColorBrush).Color; } }
        private Color ValueAreaColor { get { return ((SolidColorBrush)ValueAreaColorBrush).Color; } }
        private Color NakedPocColor { get { return ((SolidColorBrush)NakedPocColorBrush).Color; } }
        private Color LabelColor { get { return ((SolidColorBrush)LabelColorBrush).Color; } }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Colorful, configurable Volume Profile with POC, Value Area, naked POC tracking and gradient shading.";
                Name = "VolumeProfilePro";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DisplayInDataBox = false;
                PaintPriceMarkers = false;
                IsSuspendedWhileInactive = true;

                Source = VolumeProfileSource.Volume;
                Range = VolumeProfileRange.Session;
                LookbackBars = 200;
                RowHeightTicks = 4;
                ValueAreaPercent = 70;
                ProfileWidthPercent = 25;
                ShowPoc = true;
                ShowValueArea = true;
                ShowNakedPoc = true;
                ShowLabels = true;
                MaxSessionsToShow = 3;
                ProfileOpacity = 70;

                LowVolumeColorBrush = Brushes.MidnightBlue;
                MidVolumeColorBrush = Brushes.MediumSpringGreen;
                HighVolumeColorBrush = Brushes.OrangeRed;
                PocColorBrush = Brushes.Yellow;
                ValueAreaColorBrush = Brushes.DodgerBlue;
                NakedPocColorBrush = Brushes.Magenta;
                LabelColorBrush = Brushes.White;
            }
            else if (State == State.Configure)
            {
            }
            else if (State == State.DataLoaded)
            {
                sessions.Clear();
                currentSession = null;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 1)
                return;

            tickSizeRows = Instrument.MasterInstrument.TickSize * Math.Max(1, RowHeightTicks);

            bool newSession = false;

            if (Range == VolumeProfileRange.Session)
            {
                newSession = Bars.IsFirstBarOfSession;
            }
            else
            {
                newSession = currentSession == null || (CurrentBar - currentSession.StartBarIdx) >= LookbackBars;
            }

            if (newSession || currentSession == null)
            {
                currentSession = new ProfileSession
                {
                    StartTime = Time[0],
                    StartBarIdx = CurrentBar
                };
                sessions.Add(currentSession);

                while (sessions.Count > Math.Max(1, MaxSessionsToShow))
                    sessions.RemoveAt(0);
            }

            currentSession.EndTime = Time[0];
            currentSession.EndBarIdx = CurrentBar;

            double rowPrice = Math.Round(Low[0] / tickSizeRows) * tickSizeRows;
            double topPrice = Math.Round(High[0] / tickSizeRows) * tickSizeRows;
            double value = Source == VolumeProfileSource.Volume ? Volume[0] : 1.0;

            int rowCount = Math.Max(1, (int)Math.Round((topPrice - rowPrice) / tickSizeRows) + 1);
            double perRow = value / rowCount;

            for (double p = rowPrice; p <= topPrice + 1e-9; p += tickSizeRows)
            {
                double key = Math.Round(p / tickSizeRows) * tickSizeRows;
                if (!currentSession.Rows.ContainsKey(key))
                    currentSession.Rows[key] = 0;
                currentSession.Rows[key] += perRow;
            }

            RecalculateSessionStats(currentSession);
            UpdateNakedPocs();
        }

        private void RecalculateSessionStats(ProfileSession session)
        {
            if (session.Rows.Count == 0)
                return;

            var ordered = session.Rows.OrderByDescending(kv => kv.Value).ToList();
            session.Poc = ordered.First().Key;

            double total = session.Rows.Values.Sum();
            double target = total * (ValueAreaPercent / 100.0);

            var byPrice = session.Rows.Keys.OrderBy(k => k).ToList();
            int pocIdx = byPrice.IndexOf(session.Poc);
            double accumulated = session.Rows[session.Poc];
            int lo = pocIdx, hi = pocIdx;

            while (accumulated < target && (lo > 0 || hi < byPrice.Count - 1))
            {
                double belowVal = lo > 0 ? session.Rows[byPrice[lo - 1]] : -1;
                double aboveVal = hi < byPrice.Count - 1 ? session.Rows[byPrice[hi + 1]] : -1;

                if (aboveVal >= belowVal && hi < byPrice.Count - 1)
                {
                    hi++;
                    accumulated += session.Rows[byPrice[hi]];
                }
                else if (lo > 0)
                {
                    lo--;
                    accumulated += session.Rows[byPrice[lo]];
                }
                else
                {
                    break;
                }
            }

            session.Val = byPrice[lo];
            session.Vah = byPrice[hi];
        }

        private void UpdateNakedPocs()
        {
            if (sessions.Count < 2)
                return;

            for (int i = 0; i < sessions.Count - 1; i++)
            {
                var s = sessions[i];
                if (double.IsNaN(s.Poc))
                    continue;

                s.PocFilled = false;
                for (int j = i + 1; j < sessions.Count; j++)
                {
                    var later = sessions[j];
                    if (later.Rows.Keys.Any(k => k <= s.Poc) && later.Rows.Keys.Any(k => k >= s.Poc))
                    {
                        if (later.Rows.Keys.Min() <= s.Poc && later.Rows.Keys.Max() >= s.Poc)
                        {
                            s.PocFilled = true;
                            break;
                        }
                    }
                }
            }
        }

        protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
        {
            base.OnRender(chartControl, chartScale);

            if (sessions.Count == 0 || ChartBars == null)
                return;

            var rt = RenderTarget;

            foreach (var session in sessions)
            {
                if (session.Rows.Count == 0)
                    continue;

                int startBarX = chartControl.GetXByBarIndex(ChartBars, session.StartBarIdx);
                int endBarIndexForWidth = Range == VolumeProfileRange.Session
                    ? GetNextSessionBoundary(session)
                    : session.EndBarIdx;

                int sessionPixelWidth = Math.Max(20, chartControl.GetXByBarIndex(ChartBars, endBarIndexForWidth) - startBarX);
                int profilePixelWidth = (int)(sessionPixelWidth * (ProfileWidthPercent / 100.0));

                double maxVal = session.Rows.Values.Max();
                byte alpha = (byte)(255 * (ProfileOpacity / 100.0));

                foreach (var kv in session.Rows.OrderBy(r => r.Key))
                {
                    double price = kv.Key;
                    double val = kv.Value;
                    float y = chartScale.GetYByValue(price);
                    float yNext = chartScale.GetYByValue(price + tickSizeRows);
                    float rowHeight = Math.Abs(y - yNext);
                    if (rowHeight < 1) rowHeight = 1;

                    double ratio = maxVal > 0 ? val / maxVal : 0;
                    Color rowColor = GetGradientColor(ratio);
                    rowColor.A = alpha;

                    bool isVa = ShowValueArea && price >= session.Val && price <= session.Vah;
                    if (isVa)
                    {
                        rowColor = Lerp(rowColor, ValueAreaColor, 0.25);
                    }

                    int barWidth = (int)(profilePixelWidth * ratio);
                    if (barWidth < 1) barWidth = 1;

                    var rect = new SharpDX.RectangleF(startBarX, Math.Min(y, yNext), barWidth, rowHeight);

                    using (var brush = new SolidColorBrush(rowColor).ToDxBrush(rt))
                    {
                        rt.FillRectangle(rect, brush);
                    }

                    if (ShowLabels && rowHeight >= 9)
                    {
                        string text = Source == VolumeProfileSource.Volume
                            ? $"{val:N0} ({val / session.Rows.Values.Sum() * 100:F1}%)"
                            : $"{val:N0}";

                        using (var labelBrush = new SolidColorBrush(LabelColor).ToDxBrush(rt))
                        {
                            var textLayout = new SharpDX.DirectWrite.TextFormat(
                                Core.Globals.DirectWriteFactory, "Arial", 9f);
                            rt.DrawText(text, textLayout,
                                new SharpDX.RectangleF(startBarX + barWidth + 3, Math.Min(y, yNext) - 1, 120, rowHeight + 2),
                                labelBrush);
                            textLayout.Dispose();
                        }
                    }
                }

                if (ShowPoc && !double.IsNaN(session.Poc))
                {
                    DrawHorizontalMarker(rt, chartControl, chartScale, session.Poc, startBarX,
                        startBarX + sessionPixelWidth, PocColor, 2);
                }

                if (ShowValueArea && !double.IsNaN(session.Vah) && !double.IsNaN(session.Val))
                {
                    DrawHorizontalMarker(rt, chartControl, chartScale, session.Vah, startBarX,
                        startBarX + sessionPixelWidth, ValueAreaColor, 1);
                    DrawHorizontalMarker(rt, chartControl, chartScale, session.Val, startBarX,
                        startBarX + sessionPixelWidth, ValueAreaColor, 1);
                }

                if (ShowNakedPoc && !session.PocFilled && !double.IsNaN(session.Poc))
                {
                    int chartRightX = chartControl.GetXByBarIndex(ChartBars, ChartBars.ToIndex);
                    DrawHorizontalMarker(rt, chartControl, chartScale, session.Poc,
                        startBarX + sessionPixelWidth, chartRightX, NakedPocColor, 2, true);
                }
            }
        }

        private int GetNextSessionBoundary(ProfileSession session)
        {
            int idx = sessions.IndexOf(session);
            if (idx >= 0 && idx < sessions.Count - 1)
                return sessions[idx + 1].StartBarIdx;
            return Math.Min(CurrentBar, session.EndBarIdx + Math.Max(10, (session.EndBarIdx - session.StartBarIdx)));
        }

        private void DrawHorizontalMarker(SharpDX.Direct2D1.RenderTarget rt, ChartControl chartControl,
            ChartScale chartScale, double price, int x1, int x2, Color color, float thickness, bool dashed = false)
        {
            float y = chartScale.GetYByValue(price);
            using (var brush = new SolidColorBrush(color).ToDxBrush(rt))
            {
                var strokeStyle = dashed
                    ? new SharpDX.Direct2D1.StrokeStyle(Core.Globals.D2DFactory,
                        new SharpDX.Direct2D1.StrokeStyleProperties { DashStyle = SharpDX.Direct2D1.DashStyle.Dash })
                    : null;

                rt.DrawLine(new SharpDX.Vector2(x1, y), new SharpDX.Vector2(x2, y), brush, thickness, strokeStyle);
                strokeStyle?.Dispose();
            }
        }

        private Color GetGradientColor(double ratio)
        {
            ratio = Math.Max(0, Math.Min(1, ratio));
            if (ratio < 0.5)
                return Lerp(LowVolumeColor, MidVolumeColor, ratio * 2);
            return Lerp(MidVolumeColor, HighVolumeColor, (ratio - 0.5) * 2);
        }

        private Color Lerp(Color a, Color b, double t)
        {
            t = Math.Max(0, Math.Min(1, t));
            return Color.FromArgb(
                (byte)(a.A + (b.A - a.A) * t),
                (byte)(a.R + (b.R - a.R) * t),
                (byte)(a.G + (b.G - a.G) * t),
                (byte)(a.B + (b.B - a.B) * t));
        }

        #region Properties

        [NinjaScriptProperty]
        [Display(Name = "Volume Source", GroupName = "Profile Settings", Order = 1)]
        public VolumeProfileSource Source { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Range Mode", GroupName = "Profile Settings", Order = 2)]
        public VolumeProfileRange Range { get; set; }

        [NinjaScriptProperty]
        [Range(10, 5000)]
        [Display(Name = "Lookback Bars (Fixed Range)", GroupName = "Profile Settings", Order = 3)]
        public int LookbackBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Row Height (Ticks)", GroupName = "Profile Settings", Order = 4)]
        public int RowHeightTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 99)]
        [Display(Name = "Value Area %", GroupName = "Profile Settings", Order = 5)]
        public int ValueAreaPercent { get; set; }

        [NinjaScriptProperty]
        [Range(5, 100)]
        [Display(Name = "Profile Width %", GroupName = "Display", Order = 1)]
        public int ProfileWidthPercent { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max Sessions To Show", GroupName = "Display", Order = 2)]
        public int MaxSessionsToShow { get; set; }

        [NinjaScriptProperty]
        [Range(10, 100)]
        [Display(Name = "Profile Opacity %", GroupName = "Display", Order = 3)]
        public int ProfileOpacity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Show POC Line", GroupName = "Display", Order = 4)]
        public bool ShowPoc { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Show Value Area", GroupName = "Display", Order = 5)]
        public bool ShowValueArea { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Show Naked POC", GroupName = "Display", Order = 6)]
        public bool ShowNakedPoc { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Show Row Labels", GroupName = "Display", Order = 7)]
        public bool ShowLabels { get; set; }

        [NinjaScriptProperty]
        [XmlIgnore]
        [Display(Name = "Low Volume Color", GroupName = "Colors", Order = 1)]
        public Brush LowVolumeColorBrush { get; set; }
        [Browsable(false)]
        public string LowVolumeColorBrushSerialize
        {
            get { return Serialize.BrushToString(LowVolumeColorBrush); }
            set { LowVolumeColorBrush = Serialize.StringToBrush(value); }
        }

        [NinjaScriptProperty]
        [XmlIgnore]
        [Display(Name = "Mid Volume Color", GroupName = "Colors", Order = 2)]
        public Brush MidVolumeColorBrush { get; set; }
        [Browsable(false)]
        public string MidVolumeColorBrushSerialize
        {
            get { return Serialize.BrushToString(MidVolumeColorBrush); }
            set { MidVolumeColorBrush = Serialize.StringToBrush(value); }
        }

        [NinjaScriptProperty]
        [XmlIgnore]
        [Display(Name = "High Volume Color", GroupName = "Colors", Order = 3)]
        public Brush HighVolumeColorBrush { get; set; }
        [Browsable(false)]
        public string HighVolumeColorBrushSerialize
        {
            get { return Serialize.BrushToString(HighVolumeColorBrush); }
            set { HighVolumeColorBrush = Serialize.StringToBrush(value); }
        }

        [NinjaScriptProperty]
        [XmlIgnore]
        [Display(Name = "POC Color", GroupName = "Colors", Order = 4)]
        public Brush PocColorBrush { get; set; }
        [Browsable(false)]
        public string PocColorBrushSerialize
        {
            get { return Serialize.BrushToString(PocColorBrush); }
            set { PocColorBrush = Serialize.StringToBrush(value); }
        }

        [NinjaScriptProperty]
        [XmlIgnore]
        [Display(Name = "Value Area Color", GroupName = "Colors", Order = 5)]
        public Brush ValueAreaColorBrush { get; set; }
        [Browsable(false)]
        public string ValueAreaColorBrushSerialize
        {
            get { return Serialize.BrushToString(ValueAreaColorBrush); }
            set { ValueAreaColorBrush = Serialize.StringToBrush(value); }
        }

        [NinjaScriptProperty]
        [XmlIgnore]
        [Display(Name = "Naked POC Color", GroupName = "Colors", Order = 6)]
        public Brush NakedPocColorBrush { get; set; }
        [Browsable(false)]
        public string NakedPocColorBrushSerialize
        {
            get { return Serialize.BrushToString(NakedPocColorBrush); }
            set { NakedPocColorBrush = Serialize.StringToBrush(value); }
        }

        [NinjaScriptProperty]
        [XmlIgnore]
        [Display(Name = "Label Color", GroupName = "Colors", Order = 7)]
        public Brush LabelColorBrush { get; set; }
        [Browsable(false)]
        public string LabelColorBrushSerialize
        {
            get { return Serialize.BrushToString(LabelColorBrush); }
            set { LabelColorBrush = Serialize.StringToBrush(value); }
        }

        #endregion
    }
}
