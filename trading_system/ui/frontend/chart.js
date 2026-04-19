/**
 * TradingView Lightweight Charts Integration
 * Handles candlestick chart rendering and updates
 */

class ChartManager {
    constructor(containerId) {
        this.containerId = containerId;
        this.chart = null;
        this.candlestickSeries = null;
        this.volumeSeries = null;
        this.currentSymbol = null;
        
        this.initChart();
    }
    
    initChart() {
        const container = document.getElementById(this.containerId);
        
        if (!container) {
            console.error('Chart container not found');
            return;
        }
        
        // Create chart
        this.chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: container.clientHeight,
            layout: {
                background: { color: '#161b22' },
                textColor: '#c9d1d9',
            },
            grid: {
                vertLines: { color: '#30363d' },
                horzLines: { color: '#30363d' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#30363d',
            },
            timeScale: {
                borderColor: '#30363d',
                timeVisible: true,
                secondsVisible: false,
            },
        });
        
        // Add candlestick series
        this.candlestickSeries = this.chart.addCandlestickSeries({
            upColor: '#3fb950',
            downColor: '#f85149',
            borderUpColor: '#3fb950',
            borderDownColor: '#f85149',
            wickUpColor: '#3fb950',
            wickDownColor: '#f85149',
        });
        
        // Add volume series (optional)
        this.volumeSeries = this.chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '',
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.resize();
        });
        
        console.log('✅ Chart initialized');
    }
    
    resize() {
        if (!this.chart) return;
        
        const container = document.getElementById(this.containerId);
        if (container) {
            this.chart.applyOptions({
                width: container.clientWidth,
                height: container.clientHeight,
            });
        }
    }
    
    updateData(symbol, data) {
        if (!this.chart || !this.candlestickSeries) {
            console.error('Chart not initialized');
            return;
        }
        
        this.currentSymbol = symbol;
        
        try {
            // Clear existing data
            this.candlestickSeries.setData([]);
            this.volumeSeries.setData([]);
            
            // Prepare candlestick data
            const candleData = data.map(candle => ({
                time: candle.time,
                open: candle.open,
                high: candle.high,
                low: candle.low,
                close: candle.close,
            }));
            
            // Prepare volume data
            const volumeData = data.map(candle => ({
                time: candle.time,
                value: candle.volume,
                color: candle.close >= candle.open ? 'rgba(63, 185, 80, 0.5)' : 'rgba(248, 81, 73, 0.5)',
            }));
            
            // Set data
            this.candlestickSeries.setData(candleData);
            this.volumeSeries.setData(volumeData);
            
            // Fit content
            this.chart.timeScale().fitContent();
            
            console.log(`✅ Chart updated for ${symbol} with ${data.length} candles`);
        } catch (error) {
            console.error('Error updating chart:', error);
        }
    }
    
    clearChart() {
        if (this.candlestickSeries) {
            this.candlestickSeries.setData([]);
        }
        if (this.volumeSeries) {
            this.volumeSeries.setData([]);
        }
        this.currentSymbol = null;
    }
    
    destroy() {
        if (this.chart) {
            this.chart.remove();
            this.chart = null;
        }
    }
}

// Export for use in app.js
window.ChartManager = ChartManager;

