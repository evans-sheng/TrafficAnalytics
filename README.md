# Traffic Data Governance and Congestion Mitigation Optimization Software

A traffic data governance and congestion mitigation optimization platform featuring data processing and visualization capabilities.

## 📋 Project Overview

This project is an intelligent traffic large-screen visualization system designed to provide real-time traffic monitoring, data analysis, and decision support for traffic management departments through data analysis and visualization technologies. The system adopts a front-end and back-end separation architecture, providing an intuitive large-screen display interface and powerful data processing capabilities.

## 🏗️ System Architecture

```
TrafficAnalytics/
├── code/
│   └── LargeScreenFront/          # Frontend Application
│       ├── src/
│       │   ├── components/        # Vue Components
│       │   ├── utils/            # Utility Functions
│       │   ├── router/           # Router Configuration
│       │   └── assets/           # Static Assets
│       ├── public/               # Public Resources
│       └── package.json          # Dependencies Configuration
├── docs/                         # Documentation Directory
├── data/                         # Data Directory
└── README.md                     # Project Documentation
```

## ✨ Core Features

### 🖥️ Large Screen Visualization
- **Smart Traffic Dashboard**: Professional traffic monitoring large-screen interface
- **Real-time Data Display**: Current traffic flow, incident count, average speed and other key indicators
- **Multi-dimensional Charts**: Traffic flow analysis by direction (NW, NE, SW, SE) and lanes
- **Chart Interaction**: Support for chart zoom in/out and detailed data viewing

### 🗺️ Map Visualization
- **Interactive Maps**: High-performance map display based on Leaflet
- **Location Markers**: Support for location point markers in multiple coordinate systems
- **Coordinate Conversion**: Support conversion between WGS84 (GPS), GCJ02 (Mars Coordinate System), BD09 (Baidu Coordinate System)
- **Dynamic Styling**: Automatic adjustment of marker styles and sizes based on data volume

### 📊 Data Processing
- **CSV Data Loading**: Support for importing and parsing traffic flow data from CSV files
- **Time Series Analysis**: Analysis of traffic flow trends by time dimension
- **Multi-intersection Support**: Support for data switching and comparative analysis of multiple intersections
- **Real-time Data Updates**: Support for 1-minute and 15-minute granularity data display

## 🛠️ Technology Stack

### Frontend Technologies
- **Framework**: Vue 3 + Vite
- **Routing**: Vue Router 4
- **Charts**: ECharts 5.6.0
- **Maps**: Leaflet 1.9.4
- **Build Tool**: Vite 6.3.5
- **Development Language**: JavaScript ES6+

### Backend Technologies
- **Framework**: Java + Spring Boot
- **Database**: Support for multiple databases
- **API**: RESTful API design
- **Data Processing**: Real-time traffic data processing and analysis

## 🚀 Quick Start

### Environment Requirements
- Node.js >= 16.0.0
- npm >= 8.0.0
- Java >= 8 (Backend)
- Maven >= 3.6.0 (Backend)

### Frontend Installation and Running

1. **Clone the Project**
```bash
git clone <repository-url>
cd TrafficAnalytics
```

2. **Install Frontend Dependencies**
```bash
cd code/LargeScreenFront
npm install
```

3. **Start Development Server**
```bash
npm run dev
```

4. **Build for Production**
```bash
npm run build
```

5. **Preview Production Build**
```bash
npm run preview
```

### Backend Installation and Running

1. **Compile Backend Project**
```bash
# Execute in the backend project root directory
mvn clean compile
```

2. **Run Backend Service**
```bash
mvn spring-boot:run
```

3. **Package and Deploy**
```bash
mvn clean package
java -jar target/traffic-analytics-backend.jar
```

## 📱 Page Features

### Main Page (/)
- Real-time traffic statistics display
- Traffic flow charts for four directions
- Dynamic switching of intersections, time ranges, and data granularity
- Chart zoom-in viewing functionality

### Map Page (/map)
- Interactive map interface
- Traffic monitoring point markers
- Support for multiple coordinate system switching
- Detailed information popups for points

## 🔧 Configuration Instructions

### Data Configuration
- Traffic flow data placed in the `src/assets/data/` directory
- Support for CSV data formats with 1-minute and 15-minute granularity
- Location data supports JSON format longitude and latitude information

### Coordinate System Configuration
The system supports three coordinate systems:
- **WGS84**: GPS standard coordinate system
- **GCJ02**: Mars coordinate system (Amap, Tencent Maps)
- **BD09**: Baidu coordinate system

### API Endpoints
```javascript
// Example API endpoints
GET /api/traffic/realtime      // Real-time traffic data
GET /api/traffic/history       // Historical traffic data
GET /api/incidents/current     // Current traffic incidents
GET /api/locations/points      // Monitoring point information
```

## 📈 Data Formats

### Traffic Flow Data Format
```csv
direction,lane,minute,vehicle_count
NW,1,2025-03-07T08:00:00Z,15
NE,2,2025-03-07T08:01:00Z,23
```

### Location Data Format
```json
{"longitude":"116.511681","latitude":"39.761152"}
```

## 🎨 Interface Features

- **Professional Large Screen Design**: Suitable for traffic monitoring center large screen displays
- **Responsive Layout**: Support for different resolution display devices
- **Real-time Clock Display**: Real-time display of current time and date at the top
- **Elegant UI Design**: Modern gradient colors and shadow effects
- **Smooth Animation Effects**: Chart switching and data update animations

## 🔒 Open Source License

This project is licensed under the **GPL (General Public License)**.

- Commercial use allowed
- Modification and distribution allowed
- Requires open source derivative works
- Provides source code access rights

## 🤝 Contributing Guidelines

Welcome to submit Issues and Pull Requests to improve the project!

1. Fork this project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support and Contact

If you have questions or suggestions, please contact us through:

- Submit GitHub Issues
- Send emails to project maintainers
- Check project documentation and Wiki

## 📝 Changelog

### v1.0.0
- Initial version release
- Implemented basic traffic data visualization functionality
- Support for multi-intersection data display
- Integrated map visualization functionality
- Implemented coordinate system conversion functionality

---

**Traffic Data Governance and Congestion Mitigation Optimization Software** - Making traffic management smarter and travel smoother! 
