"""
Reusable HTML/CSS/JS template for interactive farm maps.
Used by app.py for both Farm 157 and Farm 195.
"""


MAP_STROKE_REFERENCE_WIDTH = 4000
MAP_STROKE_WIDTH = 3
MAP_STROKE_HOVER_WIDTH = 5
MAP_STROKE_PINNED_WIDTH = 6
MAP_STROKE_SMALL_MAP_MULTIPLIER = 1.0
MAP_SMALL_MAP_ZOOM = 1.1


def build_farm_map_html(svg_polygons, legend_html, info_panel_html,
                        img_w, img_h, stage_colors_json):
    """Build self-contained HTML for an interactive farm map.

    Parameters
    ----------
    svg_polygons : str
        SVG <polygon> + <text> elements for all lots.
    legend_html : str
        Legend bar items HTML.
    info_panel_html : str
        Info panel rows HTML.
    img_w, img_h : int
        SVG viewBox dimensions.
    stage_colors_json : str
        JSON string of stage→color mapping.

    Returns
    -------
    str
        Complete HTML document string (for st.components.html).
    """
    # Scale font size relative to image width. Farm 157 (img_w=4000) used 47px.
    label_font_size = max(10, int(img_w * 47 / 4000))
    stroke_scale = (img_w / MAP_STROKE_REFERENCE_WIDTH) if img_w else 1
    if img_w and img_w < MAP_STROKE_REFERENCE_WIDTH:
        stroke_scale *= MAP_STROKE_SMALL_MAP_MULTIPLIER
    polygon_stroke_width = round(MAP_STROKE_WIDTH * stroke_scale, 2)
    polygon_hover_stroke_width = round(MAP_STROKE_HOVER_WIDTH * stroke_scale, 2)
    polygon_pinned_stroke_width = round(MAP_STROKE_PINNED_WIDTH * stroke_scale, 2)
    map_zoom = MAP_SMALL_MAP_ZOOM if img_w and img_w < MAP_STROKE_REFERENCE_WIDTH else 1
    viewbox_w = img_w / map_zoom
    viewbox_h = img_h / map_zoom
    viewbox_x = (img_w - viewbox_w) / 2
    viewbox_y = (img_h - viewbox_h) / 2

    return f'''
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        html {{
            background: transparent;
            width: 100%;
            max-width: 100%;
            overflow-x: hidden;
        }}
        body {{
            background: transparent;
            width: 100%;
            max-width: 100%;
            overflow-x: hidden;
            overflow-y: hidden;
            height: auto;
            -webkit-text-size-adjust: 100%;
        }}
        .farm-map-container {{
            position: relative;
            width: 100%;
            max-width: 100%;
            background: #1a1a2e;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #2d3460;
        }}
        .farm-map-container svg {{
            display: block;
            width: 100%;
            height: auto;
        }}
        .lot-poly {{
            fill-opacity: 0.45;
            stroke: rgba(255,255,255,0.5);
            stroke-width: {polygon_stroke_width};
            cursor: pointer;
            transition: fill-opacity 0.2s, stroke-width 0.2s;
        }}
        .lot-poly:hover {{
            fill-opacity: 0.75;
            stroke: #fff;
            stroke-width: {polygon_hover_stroke_width};
        }}
        .lot-poly.pinned {{
            fill-opacity: 0.85;
            stroke: #6366f1;
            stroke-width: {polygon_pinned_stroke_width};
        }}
        .lot-label {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: {label_font_size}px;
            font-weight: 700;
            fill: #fff;
            text-anchor: middle;
            dominant-baseline: central;
            pointer-events: none;
            text-shadow: 0 2px 6px rgba(0,0,0,0.7);
        }}
        .map-tooltip {{
            position: absolute;
            display: none;
            background: rgba(15, 23, 42, 0.96);
            color: #e2e8f0;
            border: 1px solid rgba(99,102,241,0.4);
            border-radius: 10px;
            padding: 14px 18px;
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
            line-height: 1.65;
            pointer-events: none;
            z-index: 1000;
            min-width: 240px;
            max-width: 320px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.45);
            backdrop-filter: blur(8px);
        }}
        .map-tooltip.pinned {{
            pointer-events: auto;
            max-height: 480px;
            overflow-y: auto;
            border-color: rgba(99,102,241,0.8);
            box-shadow: 0 8px 32px rgba(99,102,241,0.25), 0 8px 32px rgba(0,0,0,0.45);
        }}
        .map-tooltip.pinned::-webkit-scrollbar {{ width: 4px; }}
        .map-tooltip.pinned::-webkit-scrollbar-thumb {{ background: #4a5568; border-radius: 4px; }}
        .map-tooltip .tt-title {{
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(255,255,255,0.15);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .map-tooltip .tt-pin {{
            font-size: 12px;
            opacity: 0.6;
        }}
        .map-tooltip .tt-row {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
        }}
        .map-tooltip .tt-label {{ color: #94a3b8; }}
        .map-tooltip .tt-value {{ font-weight: 600; color: #fff; }}
        .map-tooltip .tt-stage {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .map-tooltip .tt-hint {{
            font-size: 11px;
            color: #64748b;
            margin-top: 8px;
            text-align: center;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 6px;
        }}
        .legend-bar {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 16px;
            padding: 10px 16px;
            background: #16213e;
            border-top: 1px solid #2d3460;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 12px;
            color: #94a3b8;
        }}
        .legend-dot {{
            width: 12px; height: 12px;
            border-radius: 3px;
            flex-shrink: 0;
        }}
        .map-info-panel {{
            position: absolute;
            bottom: 44px;
            left: 10px;
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(99,102,241,0.3);
            border-radius: 10px;
            padding: 10px 14px;
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 12px;
            line-height: 1.6;
            z-index: 500;
            min-width: 170px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }}
        .map-info-panel .info-title {{
            font-size: 11px;
            font-weight: 700;
            color: #cbd5e1;
            margin-bottom: 6px;
            padding-bottom: 4px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .map-info-panel .info-row {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 1px 0;
        }}
        .map-info-panel .info-label {{
            color: #94a3b8;
            white-space: nowrap;
        }}
        .map-info-panel .info-value {{
            font-weight: 700;
            white-space: nowrap;
        }}

        /* ═══════════════════════════════════════════════════
           RESPONSIVE BREAKPOINTS
           ═══════════════════════════════════════════════════ */

        /* ── Mobile: 320–480px ── */
        @media (max-width: 480px) {{
            .farm-map-container {{ border-radius: 6px; }}
            .map-tooltip {{
                min-width: 140px; max-width: 190px;
                padding: 7px 9px; font-size: 10px;
                line-height: 1.4; border-radius: 7px;
            }}
            .map-tooltip .tt-title {{ font-size: 12px; margin-bottom: 3px; padding-bottom: 3px; }}
            .map-tooltip .tt-pin {{ font-size: 9px; }}
            .map-tooltip .tt-row {{ gap: 6px; }}
            .map-tooltip .tt-stage {{ padding: 1px 5px; font-size: 9px; }}
            .map-tooltip .tt-hint {{ font-size: 8px; margin-top: 3px; padding-top: 3px; }}
            .map-tooltip.pinned {{ max-height: 240px; }}
            .legend-bar {{ gap: 6px; padding: 5px 6px; }}
            .legend-item {{ font-size: 9px; gap: 3px; }}
            .legend-dot {{ width: 8px; height: 8px; border-radius: 2px; }}
            .map-info-panel {{
                bottom: 30px; left: 4px; padding: 5px 7px;
                font-size: 9px; min-width: 110px; border-radius: 6px;
            }}
            .map-info-panel .info-title {{ font-size: 8px; margin-bottom: 2px; }}
        }}

        /* ── Small tablet / phone landscape: 481–768px ── */
        @media (min-width: 481px) and (max-width: 768px) {{
            .farm-map-container {{ border-radius: 8px; }}
            .map-tooltip {{
                min-width: 160px; max-width: 220px;
                padding: 8px 11px; font-size: 11px;
                line-height: 1.45; border-radius: 8px;
            }}
            .map-tooltip .tt-title {{ font-size: 13px; margin-bottom: 4px; padding-bottom: 4px; }}
            .map-tooltip .tt-pin {{ font-size: 10px; }}
            .map-tooltip .tt-row {{ gap: 8px; }}
            .map-tooltip .tt-stage {{ padding: 1px 6px; font-size: 10px; }}
            .map-tooltip .tt-hint {{ font-size: 9px; margin-top: 4px; padding-top: 4px; }}
            .map-tooltip.pinned {{ max-height: 300px; }}
            .legend-bar {{ gap: 8px; padding: 6px 10px; }}
            .legend-item {{ font-size: 10px; gap: 4px; }}
            .legend-dot {{ width: 9px; height: 9px; }}
            .map-info-panel {{
                bottom: 34px; left: 6px; padding: 6px 8px;
                font-size: 10px; min-width: 135px; border-radius: 7px;
            }}
            .map-info-panel .info-title {{ font-size: 9px; margin-bottom: 3px; }}
        }}

        /* ── Tablet / iPad portrait: 769–1024px ── */
        @media (min-width: 769px) and (max-width: 1024px) {{
            .farm-map-container {{ border-radius: 10px; }}
            .map-tooltip {{
                min-width: 200px; max-width: 280px;
                padding: 10px 14px; font-size: 12px;
                line-height: 1.5; border-radius: 9px;
            }}
            .map-tooltip .tt-title {{ font-size: 15px; }}
            .map-tooltip .tt-stage {{ font-size: 11px; padding: 2px 8px; }}
            .map-tooltip .tt-hint {{ font-size: 10px; }}
            .map-tooltip.pinned {{ max-height: 360px; }}
            .legend-bar {{ gap: 12px; padding: 8px 14px; }}
            .legend-item {{ font-size: 12px; gap: 5px; }}
            .legend-dot {{ width: 11px; height: 11px; }}
            .map-info-panel {{
                bottom: 40px; left: 8px; padding: 8px 11px;
                font-size: 11px; min-width: 160px; border-radius: 8px;
            }}
            .map-info-panel .info-title {{ font-size: 10px; }}
        }}

        /* ── Large: 1200–1799px (laptops, desktops) ── */
        @media (min-width: 1200px) and (max-width: 1799px) {{
            .map-tooltip {{
                min-width: 280px; max-width: 380px;
                padding: 16px 20px; font-size: 14px;
            }}
            .map-tooltip .tt-title {{ font-size: 18px; }}
            .map-tooltip .tt-stage {{ font-size: 13px; padding: 3px 12px; }}
            .map-tooltip .tt-hint {{ font-size: 12px; }}
            .legend-bar {{ gap: 20px; padding: 12px 20px; }}
            .legend-item {{ font-size: 14px; }}
            .legend-dot {{ width: 14px; height: 14px; }}
            .map-info-panel {{
                bottom: 50px; padding: 12px 16px;
                font-size: 13px; min-width: 200px;
            }}
            .map-info-panel .info-title {{ font-size: 12px; }}
        }}

        /* ── XL: 1800px+ (large monitors, 4K, ultrawide) ── */
        @media (min-width: 1800px) {{
            .map-tooltip {{
                min-width: 340px; max-width: 460px;
                padding: 20px 26px; font-size: 15px;
                line-height: 1.7;
            }}
            .map-tooltip .tt-title {{ font-size: 20px; margin-bottom: 10px; }}
            .map-tooltip .tt-stage {{ font-size: 14px; padding: 4px 14px; }}
            .map-tooltip .tt-hint {{ font-size: 13px; }}
            .map-tooltip.pinned {{ max-height: 600px; }}
            .legend-bar {{ gap: 24px; padding: 14px 24px; }}
            .legend-item {{ font-size: 15px; gap: 8px; }}
            .legend-dot {{ width: 16px; height: 16px; border-radius: 4px; }}
            .map-info-panel {{
                bottom: 56px; padding: 14px 18px;
                font-size: 14px; min-width: 220px; border-radius: 12px;
            }}
            .map-info-panel .info-title {{ font-size: 13px; }}
        }}
    </style>

    <div class="farm-map-container" id="farmMapContainer">
        <svg viewBox="{viewbox_x:.2f} {viewbox_y:.2f} {viewbox_w:.2f} {viewbox_h:.2f}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
            <rect width="{img_w}" height="{img_h}" fill="#1a1a2e"/>
            {svg_polygons}
        </svg>
        <div class="map-tooltip" id="mapTooltip"></div>
        <div class="map-info-panel">
            <div class="info-title">Diện tích Farm</div>
            {info_panel_html}
        </div>
        <div class="legend-bar">{legend_html}</div>
    </div>

    <script>
    (function() {{
        const container = document.getElementById('farmMapContainer');
        const tooltip = document.getElementById('mapTooltip');
        const polys = container.querySelectorAll('.lot-poly');
        const stageColors = {stage_colors_json};
        stageColors["Chưa có dữ liệu"] = "#636e72";

        let pinned = false;
        let pinnedPoly = null;

        function buildHTML(d, showPin) {{
            let batches = [];
            try {{ batches = JSON.parse(d.batches || '[]'); }} catch(e) {{}}

            let pinIcon = showPin ? '<span class="tt-pin">📌 Đã ghim</span>' : '<span class="tt-pin"></span>';
            let html = '<div class="tt-title"><span>Lô ' + d.name + '</span>' + pinIcon + '</div>';
            html += '<div class="tt-row"><span class="tt-label">Diện tích lô</span><span class="tt-value">' + d.areaHa + '</span></div>';
            html += '<div class="tt-row"><span class="tt-label">Diện tích trồng</span><span class="tt-value">' + d.dtTrong + '</span></div>';
            html += '<div class="tt-row"><span class="tt-label">Tổng số cây</span><span class="tt-value">' + parseInt(d.total||0).toLocaleString() + '</span></div>';

            if (batches.length > 0) {{
                html += '<div style="border-top:1px solid rgba(255,255,255,0.1);margin:8px 0"></div>';
                for (var i = 0; i < batches.length; i++) {{
                    var b = batches[i];
                    var sc = stageColors[b.gd] || "#636e72";
                    html += '<div style="margin-bottom:' + (i < batches.length-1 ? '8' : '0') + 'px;padding:6px 8px;background:rgba(255,255,255,0.04);border-radius:6px;border-left:3px solid ' + sc + '">';
                    var batchTitle = (b.multi && b.dot) ? ('Đợt ' + b.dot + ' (' + b.vu + ')') : b.vu;
                    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px"><span style="font-weight:700;color:#fff">' + batchTitle + '</span><span class="tt-stage" style="background:' + sc + ';color:#fff">' + b.gd + '</span></div>';
                    html += '<div class="tt-row"><span class="tt-label">Bắt đầu</span><span class="tt-value">' + b.ngay_bd + '</span></div>';
                    html += '<div class="tt-row"><span class="tt-label">Số cây</span><span class="tt-value">' + b.so_cay.toLocaleString() + '</span></div>';
                    html += '<div class="tt-row"><span class="tt-label">Chích bắp</span><span class="tt-value">' + b.chich.toLocaleString() + '</span></div>';
                    html += '<div class="tt-row"><span class="tt-label">Cắt bắp</span><span class="tt-value">' + b.cat.toLocaleString() + '</span></div>';
                    html += '<div class="tt-row"><span class="tt-label">Thu hoạch</span><span class="tt-value">' + b.thu.toLocaleString() + '</span></div>';
                    html += '</div>';
                }}
            }} else {{
                html += '<div style="color:#94a3b8;margin-top:6px">Chưa có dữ liệu</div>';
            }}

            if (!showPin) {{
                html += '<div class="tt-hint">💡 Click để ghim tooltip</div>';
            }} else {{
                html += '<div class="tt-hint">Click lô khác hoặc vùng trống để bỏ ghim</div>';
            }}
            return html;
        }}

        function unpin() {{
            pinned = false;
            if (pinnedPoly) {{
                pinnedPoly.classList.remove('pinned');
                pinnedPoly = null;
            }}
            tooltip.classList.remove('pinned');
            tooltip.style.display = 'none';
        }}

        polys.forEach(poly => {{
            poly.addEventListener('mouseenter', function(e) {{
                if (pinned) return;
                tooltip.innerHTML = buildHTML(this.dataset, false);
                tooltip.style.display = 'block';
            }});

            poly.addEventListener('mousemove', function(e) {{
                if (pinned) return;
                const rect = container.getBoundingClientRect();
                const tw = tooltip.offsetWidth;
                const th = tooltip.offsetHeight;
                let x = e.clientX - rect.left + 12;
                let y = e.clientY - rect.top + 12;
                if (x + tw > rect.width) x = Math.max(4, e.clientX - rect.left - tw - 8);
                if (y + th > rect.height) y = Math.max(4, rect.height - th - 4);
                tooltip.style.left = x + 'px';
                tooltip.style.top = y + 'px';
            }});

            poly.addEventListener('mouseleave', function() {{
                if (pinned) return;
                tooltip.style.display = 'none';
            }});

            poly.addEventListener('click', function(e) {{
                e.stopPropagation();
                if (pinned && pinnedPoly === this) {{
                    unpin();
                    return;
                }}
                if (pinnedPoly) pinnedPoly.classList.remove('pinned');

                pinned = true;
                pinnedPoly = this;
                this.classList.add('pinned');
                tooltip.innerHTML = buildHTML(this.dataset, true);
                tooltip.classList.add('pinned');
                tooltip.style.display = 'block';
                tooltip.scrollTop = 0;

                const rect = container.getBoundingClientRect();
                const tw = tooltip.offsetWidth;
                const th = Math.min(tooltip.offsetHeight, rect.height - 8);
                let x = e.clientX - rect.left + 12;
                let y = e.clientY - rect.top + 12;
                if (x + tw > rect.width) x = Math.max(4, rect.width - tw - 4);
                if (y + th > rect.height) y = Math.max(4, rect.height - th - 4);
                tooltip.style.left = x + 'px';
                tooltip.style.top = y + 'px';
                tooltip.style.maxHeight = (rect.height - y - 4) + 'px';
            }});
        }});

        container.addEventListener('click', function(e) {{
            if (e.target.closest('.lot-poly') || e.target.closest('.map-tooltip')) return;
            if (pinned) unpin();
        }});

        tooltip.addEventListener('click', function(e) {{
            e.stopPropagation();
        }});

        // ── Auto-fit iframe height to content ──
        (function() {{
            var lastH = 0;
            function fitHeight() {{
                var c = document.querySelector('.farm-map-container');
                if (!c) return;
                var h = c.getBoundingClientRect().height;
                if (h < 50) return;
                h = Math.ceil(h) + 2;
                if (h === lastH) return;
                lastH = h;
                try {{
                    var frame = window.frameElement;
                    frame.style.height = h + 'px';
                    var wrapper = frame.parentElement;
                    if (wrapper) {{
                        wrapper.style.height = h + 'px';
                    }}
                }} catch(e) {{
                    document.body.style.height = h + 'px';
                }}
            }}
            if ('ResizeObserver' in window) {{
                new ResizeObserver(fitHeight).observe(document.querySelector('.farm-map-container'));
            }}
            window.addEventListener('resize', fitHeight);
            window.addEventListener('load', fitHeight);
            var polls = [50, 150, 300, 500, 800, 1200, 2000, 3000];
            polls.forEach(function(ms) {{ setTimeout(fitHeight, ms); }});
        }})();
    }})();
    </script>
    '''
