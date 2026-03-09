// Format the current date
document.getElementById('current-date').textContent = new Date().toLocaleDateString('fr-FR', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
});

// Settings & Theme
const layoutConfig = {
    font: { family: 'Inter, sans-serif', color: '#e6edf3' },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 40, b: 40, l: 40, r: 20 },
    hovermode: 'closest'
};

const colors = {
    primary: '#58a6ff',
    secondary: '#a371f7',
    success: '#2ea043',
    danger: '#f85149',
    grid: 'rgba(255,255,255,0.08)'
};

// Utils
const fetchJSON = async (url) => {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error(`Error loading ${url}:`, e);
        return [];
    }
};

// Update KPIs
const updateKPIs = (meteo, regions, poitiers) => {
    if(meteo.length > 0) {
        let sumTemp = meteo.reduce((acc, curr) => acc + (curr.Temperature || 0), 0);
        document.getElementById('avg-temp').innerText = (sumTemp / meteo.length).toFixed(1) + ' °C';
        document.getElementById('total-cities').innerText = meteo.length;
    }

    if(regions.length > 0) {
        // filter for recent year, e.g. 2023 or 2024
        let recentData = regions.filter(r => r.Annee >= 2023);
        if(recentData.length === 0) recentData = regions; // fallback
        
        let sumRain = recentData.reduce((acc, curr) => acc + (curr.Pluie || 0), 0);
        let rainKPI = '0 mm';
        if(recentData.length > 0) {
            rainKPI = (sumRain / recentData.length).toFixed(1) + ' mm';
        }
        document.getElementById('avg-rain').innerText = rainKPI;
    }

    if(poitiers.length > 0) {
        document.getElementById('poitiers-count').innerText = poitiers.length;
    }
};

// Plot Map (Données 2023)
const plotMap = (data) => {
    if (!data || data.length === 0) return;

    // Filter valid lat/lon
    const validData = data.filter(d => d.lat && d.lon && d.Temperature !== null);
    
    const trace = {
        type: 'scattermapbox',
        lon: validData.map(d => d.lon),
        lat: validData.map(d => d.lat),
        text: validData.map(d => `${d.Ville}<br>Temp: ${d.Temperature.toFixed(1)}°C`),
        mode: 'markers',
        marker: {
            size: 10,
            color: validData.map(d => d.Temperature),
            colorscale: [
                [0, '#3182ce'],      // Blue (Cold)
                [0.5, '#f6e05e'],    // Yellow (Mild)
                [1, '#e53e3e']       // Red (Hot)
            ],
            showscale: true,
            colorbar: {
                title: 'Temp (°C)',
                ticksuffix: '°C',
                outlinewidth: 0,
                tickfont: { color: layoutConfig.font.color }
            }
        },
        hovertemplate: '<b>%{text}</b><extra></extra>'
    };

    const layout = {
        ...layoutConfig,
        mapbox: {
            style: 'carto-darkmatter',
            center: { lon: 2.2137, lat: 46.2276 }, // Center of France
            zoom: 4.8
        },
        margin: { t: 0, b: 0, l: 0, r: 0 }
    };

    Plotly.newPlot('chart-map', [trace], layout, {responsive: true});
};

// Plot Region Comparison
const plotRegion = (data) => {
    if (!data || data.length === 0) return;

    // We'll prepare a grouped bar chart
    // 1 trace per Annee
    const years = [...new Set(data.map(d => d.Annee))].sort();
    
    // Get unique regions
    const regions = [...new Set(data.map(d => d.Region))].sort();
    
    const traces = years.map((year, idx) => {
        const yearData = data.filter(d => d.Annee === year);
        // Map data to regions
        const yValues = regions.map(r => {
            const match = yearData.find(d => d.Region === r);
            return match ? match.Temperature : null;
        });

        // Use a nice color palette for years
        const colorPalette = ['#58a6ff', '#a371f7', '#2ea043', '#f85149', '#f6e05e', '#ed8936'];
        
        return {
            x: regions,
            y: yValues,
            name: `${year}`,
            type: 'bar',
            marker: { color: colorPalette[idx % colorPalette.length], opacity: 0.85 },
            hovertemplate: '%{x}<br>Année: %{name}<br>Temp: %{y:.1f}°C<extra></extra>'
        };
    });

    const layout = {
        ...layoutConfig,
        barmode: 'group',
        xaxis: { 
            title: '', 
            tickangle: -45, 
            gridcolor: colors.grid,
            tickfont: { size: 10 }
        },
        yaxis: { 
            title: 'Température Moyenne (°C)', 
            gridcolor: colors.grid 
        },
        legend: { x: 0, y: 1.1, orientation: 'h', font: { color: layoutConfig.font.color } }
    };

    Plotly.newPlot('chart-region', traces, layout, {responsive: true});
};

// Plot Poitiers Focus
const plotPoitiers = (data) => {
    if (!data || data.length === 0) return;

    // Sort by Date
    const sortedData = data.sort((a, b) => new Date(a.Date) - new Date(b.Date));
    
    const traceTemp = {
        x: sortedData.map(d => d.Date),
        y: sortedData.map(d => d.Temperature),
        name: 'Température (°C)',
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: colors.primary, width: 3, shape: 'spline' },
        marker: { size: 6 }
    };

    const traceRain = {
        x: sortedData.map(d => d.Date),
        y: sortedData.map(d => d.Pluie_24h),
        name: 'Précipitations (mm)',
        type: 'bar',
        yaxis: 'y2',
        marker: { color: 'rgba(46, 160, 67, 0.5)' }
    };

    const layout = {
        ...layoutConfig,
        xaxis: {
            title: 'Date',
            gridcolor: colors.grid,
            type: 'category'
        },
        yaxis: {
            title: 'Température (°C)',
            titlefont: { color: colors.primary },
            tickfont: { color: colors.primary },
            gridcolor: colors.grid
        },
        yaxis2: {
            title: 'Précipitations (mm)',
            titlefont: { color: colors.success },
            tickfont: { color: colors.success },
            overlaying: 'y',
            side: 'right',
            showgrid: false
        },
        legend: { x: 0, y: 1.1, orientation: 'h' },
        hovermode: 'x unified'
    };

    Plotly.newPlot('chart-poitiers', [traceRain, traceTemp], layout, {responsive: true});
};

// Main Initialization
const initDashboard = async () => {
    const urls = {
        meteo: 'data/meteo_2023.json',
        region: 'data/region_comparison.json',
        poitiers: 'data/poitiers_data.json'
    };

    const [dataMeteo, dataRegion, dataPoitiers] = await Promise.all([
        fetchJSON(urls.meteo),
        fetchJSON(urls.region),
        fetchJSON(urls.poitiers)
    ]);

    // Update the DOM KPIs
    updateKPIs(dataMeteo, dataRegion, dataPoitiers);

    // Render Charts
    plotMap(dataMeteo);
    plotRegion(dataRegion);
    plotPoitiers(dataPoitiers);
};

// Run when DOM is ready
document.addEventListener('DOMContentLoaded', initDashboard);
