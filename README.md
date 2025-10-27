# Dashboard Project - Fusion 4

## Overview
[Brief description of your project]

## Project Structure
- `Dashboard/`: Main Streamlit dashboard application
- `Data/`: Data storage and processing
- `Notebooks/`: Jupyter notebooks for analysis

## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/Akotet08/Applied-Data-Institute.git
cd Applied-Data-Institute
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the dashboard:
```bash
streamlit run dashboard/Home.py
```

## Contributing
1. Fork the repository
2. Create your feature branch. Example: (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Branch Strategy
- `main`: Production-ready code
- `develop`: Development branch
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `release/*`: Release preparation

## Team Members
- Sadikshya - 
- Zhomart - 
- Sinyu -  @zerisinyu
- Akotet - @Akotet08

## License
[Your chosen license]


# Pages -> Function
To edit pages, update the fuction in `uhn_dashboard.py`

1. 2_🗺️_Access_&_Coverage.py: `scene_access`
2. 3_🛠️_Service_Quality_&_Reliability.py: `scene_quality`
3. 4_💹_Financial_Health.py: `scene_finance`
4. 5_♻️_Production.py: `scene_production`