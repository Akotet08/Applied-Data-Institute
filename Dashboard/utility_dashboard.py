"""Streamlit indicator catalogue mirroring the React dashboard styling."""

from __future__ import annotations

import html
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

def _inject_base_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --brand: #4f46e5;
            --brand-dark: #3730a3;
            --brand-soft: rgba(79, 70, 229, 0.12);
            --accent-emerald: #10b981;
            --accent-sky: #0ea5e9;
            --surface: rgba(255,255,255,0.88);
            --border: rgba(148,163,184,0.32);
            --shadow: 0 24px 40px -28px rgba(30, 41, 59, 0.55);
        }

        .stApp > header {display: none;}

        .stApp {
            background: linear-gradient(145deg, #f1f5f9 0%, #ffffff 50%, #e2e8f0 100%);
            color: #1e293b;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        .block-container {
            padding-top: 2.75rem;
            padding-bottom: 4rem;
            max-width: 1220px;
        }

        .dashboard-hero {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 2.5rem;
            padding: 28px 32px;
            background: linear-gradient(135deg, rgba(79,70,229,0.16), rgba(56,189,248,0.12));
            border: 1px solid rgba(79,70,229,0.22);
            border-radius: 28px;
            box-shadow: var(--shadow);
            margin-bottom: 1.8rem;
        }

        .dashboard-hero .hero-left {
            display: flex;
            align-items: center;
            gap: 1.25rem;
        }

        .dashboard-hero .hero-icon {
            width: 60px;
            height: 60px;
            border-radius: 20px;
            background: rgba(255,255,255,0.85);
            color: var(--brand);
            display: grid;
            place-items: center;
            font-size: 1.8rem;
            box-shadow: inset 0 0 0 1px rgba(79,70,229,0.18);
        }

        .dashboard-hero h1 {
            margin: 0;
            font-size: 1.85rem;
            font-weight: 600;
            color: #111827;
            letter-spacing: -0.02em;
        }

        .dashboard-hero p {
            margin: 0.35rem 0 0;
            color: #64748b;
            font-size: 0.85rem;
        }

        .dashboard-hero .hero-stats {
            flex: 1;
            display: grid;
            gap: 12px;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        }

        .dashboard-hero .hero-stat {
            background: rgba(255,255,255,0.78);
            border-radius: 16px;
            padding: 12px 14px;
            border: 1px solid rgba(148,163,184,0.25);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
        }

        .dashboard-hero .hero-stat span {
            display: block;
        }

        .dashboard-hero .hero-stat .label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #94a3b8;
        }

        .dashboard-hero .hero-stat .value {
            font-size: 1.3rem;
            font-weight: 600;
            color: #1f2937;
            margin-top: 4px;
        }

        .panel {
            background: var(--surface);
            border: 1px solid var(--border);
            backdrop-filter: blur(28px);
            border-radius: 22px;
            padding: 24px 26px;
            box-shadow: var(--shadow);
            transition: transform 160ms ease, box-shadow 160ms ease;
        }

        .panel:hover {
            transform: translateY(-2px);
            box-shadow: 0 28px 40px -30px rgba(15,23,42,0.45);
        }

        .panel h3, .panel h4, .panel h2, .panel h5 {
            color: #111827;
        }

        .red-flags li {
            margin-bottom: 6px;
            font-size: 0.9rem;
        }

        .panel ul {
            padding-left: 1.1rem;
        }

        .panel ul li::marker {
            color: var(--brand-dark);
        }

        .footer-note {
            color: #64748b;
            font-size: 0.72rem;
            text-align: center;
            margin-top: 2.5rem;
            letter-spacing: 0.04em;
        }

        /* Tidy tables */
        div[data-testid="stDataFrame"] > div {
            border: 1px solid var(--border);
            border-radius: 14px;
            overflow: hidden;
            background: #ffffff;
            box-shadow: 0 6px 18px -8px rgba(15,23,42,0.15);
        }

        /* Tabs as pill indicators */
        div[data-testid="stTabs"] > div[role="tablist"] {
            gap: 8px;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            border: 1px solid var(--border) !important;
            border-radius: 999px !important;
            background: #ffffff !important;
            color: #1f2937 !important;
            padding: 8px 14px !important;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: var(--brand-soft) !important;
            border-color: rgba(79,70,229,0.35) !important;
            color: #111827 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


INDICATOR_DATA: List[Dict[str, str]] = [
    # Access Ladder – Water
    {
        "Domain": "Water Supply",
        "Indicator": "% population with access to surface water",
        "Description": "Percentage of the service area population drawing drinking water directly from surface sources such as rivers, dams, lakes, ponds, streams, canals, or irrigation canals.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Water Access Ladder",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% population with access to unimproved water sources",
        "Description": "Percentage of the service area population obtaining drinking water from unprotected dug wells or unprotected springs.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Water Access Ladder",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% population with access to limited water sources",
        "Description": "Percentage of the population collecting drinking water from an improved source where round-trip collection time, including queuing, exceeds 30 minutes.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Water Access Ladder",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% population with access to basic water sources",
        "Description": "Percentage of the population using an improved source with collection time of 30 minutes or less, round-trip including queuing.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "Yes",
        "CWIS Cities": "Yes",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Water Access Ladder",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% population with access to safely managed water",
        "Description": "Percentage of the population using an improved source located on premises, available when needed, and free from faecal and chemical contamination.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "Yes",
        "CWIS Cities": "Yes",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Water Access Ladder",
    },
    # Access Ladder – Sanitation
    {
        "Domain": "Sanitation",
        "Indicator": "% population practicing open defecation",
        "Description": "Percentage of the population disposing human faeces in open environments such as fields, forests, bushes, open water bodies, beaches, or with solid waste.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "Yes",
        "CWIS Cities": "Yes",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Sanitation Access Ladder",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% population with unimproved sanitation facilities",
        "Description": "Percentage of the population using pit latrines without slab or platform, hanging latrines, or bucket latrines.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Sanitation Access Ladder",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% population with limited sanitation facilities",
        "Description": "Percentage of the population using improved sanitation facilities that are shared by two or more households.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Sanitation Access Ladder",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% population with basic sanitation facilities",
        "Description": "Percentage of the population using improved sanitation facilities that are not shared with other households.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "Yes",
        "CWIS Cities": "Yes",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Sanitation Access Ladder",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% population with safely managed sanitation facilities",
        "Description": "Percentage of the population using improved, unshared sanitation facilities with excreta safely disposed in situ or treated offsite.",
        "Frequency": "Annual",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "Yes",
        "CWIS Cities": "Yes",
        "IB Net": "Somewhat",
        "Section": "Access Ladder",
        "Subcategory": "Sanitation Access Ladder",
    },
    # Coverage and expansion
    {
        "Domain": "Water Supply",
        "Indicator": "% water supply coverage",
        "Description": "Coverage percentage calculated either as (households dependent on municipal water / total households) x 100 or (piped service area / jurisdiction area) x 100.",
        "Frequency": "Quarterly",
        "Granularity": "Zone",
        "JMP": "Yes",
        "AMCOW": "Yes",
        "IWA": "—",
        "CWIS Cities": "Somewhat",
        "IB Net": "Yes",
        "Section": "Coverage & Expansion",
        "Subcategory": "Water Coverage & Expansion",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% increase in water supply coverage",
        "Description": "Percentage increase calculated as (new coverage - old coverage) / old coverage x 100 using households, population, or service area.",
        "Frequency": "Quarterly",
        "Granularity": "Zone",
        "JMP": "Somewhat",
        "AMCOW": "Yes",
        "IWA": "—",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Coverage & Expansion",
        "Subcategory": "Water Coverage & Expansion",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% increase in piped water supply",
        "Description": "Growth in piped connections calculated as (new piped connections - previous piped connections) / previous piped connections x 100.",
        "Frequency": "Quarterly",
        "Granularity": "Zone",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "—",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Coverage & Expansion",
        "Subcategory": "Water Coverage & Expansion",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% sewered connections",
        "Description": "Percentage of households (or population) with sewered connections, calculated as (sewered households / total households) x 100.",
        "Frequency": "Quarterly",
        "Granularity": "Zone",
        "JMP": "Somewhat",
        "AMCOW": "Yes",
        "IWA": "—",
        "CWIS Cities": "Yes",
        "IB Net": "Somewhat",
        "Section": "Coverage & Expansion",
        "Subcategory": "Sanitation Expansion",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% of increase in sewered connections",
        "Description": "Growth in sewered connections calculated as (new sewered connections - previous sewered connections) / previous sewered connections x 100.",
        "Frequency": "Quarterly",
        "Granularity": "Zone",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "—",
        "CWIS Cities": "Somewhat",
        "IB Net": "Somewhat",
        "Section": "Coverage & Expansion",
        "Subcategory": "Sanitation Expansion",
    },
    # Operational performance
    {
        "Domain": "Water Supply",
        "Indicator": "Non-Revenue Water",
        "Description": "Percentage of water produced that does not generate revenue: (volume produced - volume billed) / volume produced x 100.",
        "Frequency": "Monthly",
        "Granularity": "Zone",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Operational Performance",
        "Subcategory": "Network Efficiency & Quality",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "Water Quality compliance",
        "Description": "Percentage of water quality samples meeting standards: (samples meeting standards / total samples tested) x 100.",
        "Frequency": "Monthly",
        "Granularity": "Zone",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Operational Performance",
        "Subcategory": "Network Efficiency & Quality",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "Consumption per capita (l/c/d)",
        "Description": "Average consumption calculated as total water sold divided by population served (litres per capita per day).",
        "Frequency": "Monthly",
        "Granularity": "Zone",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "No",
        "Section": "Operational Performance",
        "Subcategory": "Demand & Service Levels",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "Safely managed public toilets",
        "Description": "Percentage of public spaces served with functional, safely managed sanitation facilities.",
        "Frequency": "Monthly",
        "Granularity": "Zone",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "Yes",
        "IB Net": "No",
        "Section": "Operational Performance",
        "Subcategory": "Sanitation Service Delivery",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% women in sanitation decision-making",
        "Description": "Share of women in sanitation decision-making bodies: (women in decision roles / total decision workforce) x 100.",
        "Frequency": "Quarterly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "Yes",
        "IB Net": "No",
        "Section": "Governance & Finance",
        "Subcategory": "Inclusive Governance",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "Continuity of supply (hours/day)",
        "Description": "Average hours of water supplied per day across the service area.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Operational Performance",
        "Subcategory": "Demand & Service Levels",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "24x7 water supply",
        "Description": "Percentage of continuously served customers: (continuously served customers / total connected customers) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Operational Performance",
        "Subcategory": "Demand & Service Levels",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "Wastewater collected and treated",
        "Description": "Percentage of collected wastewater that is treated: (wastewater treated / wastewater collected) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Operational Performance",
        "Subcategory": "Sanitation Service Delivery",
    },
    {
        "Domain": "Both",
        "Indicator": "% total water recycled or reused",
        "Description": "Percentage of wastewater treated and reused compared with total water supplied: (volume reused / volume supplied) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Resilience & Resource Efficiency",
        "Subcategory": "Resource Circularity",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% of faecal sludge emptied",
        "Description": "Percentage of households dependent on non-sewered sanitation that emptied faecal sludge: (households emptied / households dependent) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "—",
        "CWIS Cities": "Somewhat",
        "IB Net": "Somewhat",
        "Section": "Operational Performance",
        "Subcategory": "Sanitation Service Delivery",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% of treated faecal sludge reused",
        "Description": "Percentage of treated faecal sludge reused for productive purposes: (volume reused / volume treated) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "Yes",
        "IB Net": "Yes",
        "Section": "Resilience & Resource Efficiency",
        "Subcategory": "Resource Circularity",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% of treated wastewater reused",
        "Description": "Percentage of treated wastewater reused for productive purposes: (volume reused / volume treated) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "Yes",
        "IB Net": "Yes",
        "Section": "Resilience & Resource Efficiency",
        "Subcategory": "Resource Circularity",
    },
    {
        "Domain": "Both",
        "Indicator": "Service complaints resolution efficiency",
        "Description": "Percentage of complaints resolved: (complaints resolved / complaints received) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Operational Performance",
        "Subcategory": "Customer Service & Reliability",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "Sewer blockages",
        "Description": "Number of blockages per 100 sewer connections or per kilometre of network.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Operational Performance",
        "Subcategory": "Sanitation Service Delivery",
    },
    {
        "Domain": "Both",
        "Indicator": "Revenue collection efficiency",
        "Description": "Percentage of billed revenue collected: (revenue collected / revenue billed) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Governance & Finance",
        "Subcategory": "Financial Performance",
    },
    {
        "Domain": "Both",
        "Indicator": "Operating cost coverage",
        "Description": "Cost coverage ratio calculated as operating expenses divided by operating revenue, expressed as a percentage.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "Yes",
        "CWIS Cities": "Yes",
        "IB Net": "Yes",
        "Section": "Governance & Finance",
        "Subcategory": "Financial Performance",
    },
    {
        "Domain": "Both",
        "Indicator": "Staff efficiency",
        "Description": "Staff per 1000 connections.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Governance & Finance",
        "Subcategory": "Workforce & Capacity",
    },
    {
        "Domain": "Both",
        "Indicator": "Pro-poor financing",
        "Description": "Percentage of the served population covered by tariff systems that support low-income households: (population on supportive tariffs / population served) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "No",
        "Section": "Governance & Finance",
        "Subcategory": "Inclusive Governance",
    },
    {
        "Domain": "Both",
        "Indicator": "Utility budget variance",
        "Description": "Budget variance measured either as allocated minus actual expenditure or as (actual expenditure / allocated expenditure) x 100.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "No",
        "Section": "Governance & Finance",
        "Subcategory": "Financial Management",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% metered connections",
        "Description": "Percentage of active connections that are metered: (metered active connections / total active connections) x 100.",
        "Frequency": "Monthly",
        "Granularity": "Zone",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Yes",
        "Section": "Operational Performance",
        "Subcategory": "Network Efficiency & Quality",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% utilisation of water treatment facilities",
        "Description": "Utilisation of water treatment plants: (utilised treatment capacity / total operational design capacity) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "No",
        "Section": "Operational Performance",
        "Subcategory": "Infrastructure Utilisation",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% utilisation of wastewater or sewage treatment facilities",
        "Description": "Utilisation of sewage treatment plants: (utilised STP capacity / total operational STP capacity) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "—",
        "CWIS Cities": "Somewhat",
        "IB Net": "Somewhat",
        "Section": "Operational Performance",
        "Subcategory": "Infrastructure Utilisation",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% utilisation of faecal sludge treatment facilities",
        "Description": "Utilisation of faecal sludge treatment plants: (utilised FSTP capacity / total operational FSTP capacity) x 100.",
        "Frequency": "Monthly",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "—",
        "CWIS Cities": "Somewhat",
        "IB Net": "Somewhat",
        "Section": "Operational Performance",
        "Subcategory": "Infrastructure Utilisation",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "% national budget allocated to water",
        "Description": "Share of the national budget allocated to water: (water budget / total national budget) x 100.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "No",
        "Section": "Governance & Finance",
        "Subcategory": "Public Finance",
    },
    {
        "Domain": "Sanitation",
        "Indicator": "% national budget allocated to sanitation",
        "Description": "Share of the national budget allocated to sanitation: (sanitation budget / total national budget) x 100.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "No",
        "Section": "Governance & Finance",
        "Subcategory": "Public Finance",
    },
    {
        "Domain": "Both",
        "Indicator": "% of national budget disbursed to WASH",
        "Description": "Proportion of allocated WASH budget that is disbursed: (budget disbursed to WASH / total WASH allocation) x 100.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Yes",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "No",
        "Section": "Governance & Finance",
        "Subcategory": "Public Finance",
    },
    {
        "Domain": "Both",
        "Indicator": "% staff cost",
        "Description": "Share of staff costs within operating expenses: (staff costs / total operating expenses) x 100.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Governance & Finance",
        "Subcategory": "Financial Performance",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "Level of water stress",
        "Description": "Water stress ratio calculated as water withdrawals divided by renewable water resources.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "Yes",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Resilience & Resource Efficiency",
        "Subcategory": "Resilience & Environment",
    },
    {
        "Domain": "Both",
        "Indicator": "Water use efficiency across sectors",
        "Description": "Output per unit of water for sectors such as agriculture and manufacturing, calculated as economic output divided by water used.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "Yes",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Resilience & Resource Efficiency",
        "Subcategory": "Resilience & Environment",
    },
    {
        "Domain": "Both",
        "Indicator": "Direct economic loss from water-related disasters",
        "Description": "Monetary loss arising from floods, droughts, or pollution incidents.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "Yes",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Resilience & Resource Efficiency",
        "Subcategory": "Resilience & Environment",
    },
    {
        "Domain": "Both",
        "Indicator": "Asset health index",
        "Description": "Percentage of assets in good condition: (assets in good condition / total assets).",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "No",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Governance & Finance",
        "Subcategory": "Asset & Provider Health",
    },
    {
        "Domain": "Both",
        "Indicator": "% active service providers",
        "Description": "Percentage of registered service providers that are actively providing services: (active providers / total registered providers) x 100.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Governance & Finance",
        "Subcategory": "Asset & Provider Health",
    },
    {
        "Domain": "Water Supply",
        "Indicator": "Total registered WTPs inspected and recertified",
        "Description": "Count of registered water treatment plants inspected and recertified during the period.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Governance & Finance",
        "Subcategory": "Asset & Provider Health",
    },
    {
        "Domain": "Both",
        "Indicator": "% active licensed service providers",
        "Description": "Percentage of licensed service providers that are active: (active licensed providers / total licensed providers) x 100.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Governance & Finance",
        "Subcategory": "Asset & Provider Health",
    },
    {
        "Domain": "Both",
        "Indicator": "Complaints turnaround time",
        "Description": "Average time required to resolve service complaints.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Operational Performance",
        "Subcategory": "Customer Service & Reliability",
    },
    {
        "Domain": "Both",
        "Indicator": "% investment in human capital",
        "Description": "Share of WASH budget allocated to staff capacity building: (human capital investment / total WASH budget) x 100.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Governance & Finance",
        "Subcategory": "Workforce & Capacity",
    },
    {
        "Domain": "Both",
        "Indicator": "Staff trained (M/F)",
        "Description": "Number of staff trained during the period, disaggregated by gender.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Governance & Finance",
        "Subcategory": "Workforce & Capacity",
    },
    {
        "Domain": "Both",
        "Indicator": "Total staff numbers",
        "Description": "Total number of staff employed in WASH service provision.",
        "Frequency": "Annual",
        "Granularity": "City",
        "JMP": "No",
        "AMCOW": "Somewhat",
        "IWA": "No",
        "CWIS Cities": "No",
        "IB Net": "Somewhat",
        "Section": "Governance & Finance",
        "Subcategory": "Workforce & Capacity",
    },
]


indicator_df = pd.DataFrame(INDICATOR_DATA)

FRAMEWORK_COLUMNS = ["JMP", "AMCOW", "IWA", "CWIS Cities", "IB Net"]
FRAMEWORK_BADGE = {
    "Yes": "✅ Yes",
    "No": "—",
    "Somewhat": "➖ Somewhat",
    "—": "—",
    "": "—",
    None: "—",
}

PLOTLY_CONFIG = {"displayModeBar": False}

SECTION_ORDER = [
    "Access Ladder",
    "Coverage & Expansion",
    "Operational Performance",
    "Resilience & Resource Efficiency",
    "Governance & Finance",
    "Indicator Explorer",
]

SECTION_DESCRIPTIONS = {
    "Access Ladder": "Track the JMP-aligned water and sanitation service ladder across access levels.",
    "Coverage & Expansion": "Monitor how networks grow through new coverage, connections, and sewered service.",
    "Operational Performance": "Operational KPIs spanning efficiency, service levels, customer experience, and infrastructure utilisation.",
    "Resilience & Resource Efficiency": "Circularity, reuse, and resilience indicators linking WASH to broader sustainability goals.",
    "Governance & Finance": "Financial performance, public finance alignment, governance, and workforce capacity metrics.",
    "Indicator Explorer": "Filter, review, and export the full indicator catalogue in one place.",
}

SECTION_SUBCATEGORY_ORDER = {
    "Access Ladder": ["Water Access Ladder", "Sanitation Access Ladder"],
    "Coverage & Expansion": ["Water Coverage & Expansion", "Sanitation Expansion"],
    "Operational Performance": [
        "Network Efficiency & Quality",
        "Demand & Service Levels",
        "Sanitation Service Delivery",
        "Infrastructure Utilisation",
        "Customer Service & Reliability",
    ],
    "Resilience & Resource Efficiency": ["Resource Circularity", "Resilience & Environment"],
    "Governance & Finance": [
        "Financial Performance",
        "Financial Management",
        "Public Finance",
        "Inclusive Governance",
        "Asset & Provider Health",
        "Workforce & Capacity",
    ],
}


def slugify(text: str) -> str:
    return "".join((c.lower() if c.isalnum() else "_") for c in text).strip("_") or "data"


def style_fig(fig):
    # Clean light template to match card surfaces
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        margin=dict(l=14, r=18, t=40, b=16),
        font=dict(family="Inter, sans-serif", color="#111827"),
        hoverlabel=dict(bgcolor="rgba(17,24,39,0.96)", font_size=12, font_family="Inter"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title="", font=dict(color="#111827")),
        colorway=["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#14b8a6"],
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.25)",
        zeroline=False,
        linecolor="rgba(148,163,184,0.55)",
        tickfont=dict(color="#334155"),
        title_font=dict(color="#334155"),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.25)",
        zeroline=False,
        linecolor="rgba(148,163,184,0.55)",
        tickfont=dict(color="#334155"),
        title_font=dict(color="#334155"),
    )
    return fig


def render_plot(fig):
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def format_indicator_table(df: pd.DataFrame, include_section: bool = False) -> pd.DataFrame:
    base_cols = ["Domain", "Indicator", "Description", "Frequency", "Granularity"]
    if include_section:
        base_cols = ["Section", "Subcategory"] + base_cols
    display_df = df[base_cols + FRAMEWORK_COLUMNS].copy()
    for col in FRAMEWORK_COLUMNS:
        display_df[col] = display_df[col].map(lambda v: FRAMEWORK_BADGE.get(v, v))
    return display_df


def display_indicator_table(df: pd.DataFrame, *, include_section: bool = False, download_label: str) -> None:
    display_df = format_indicator_table(df, include_section=include_section)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download subset (CSV)",
        data=csv_bytes,
        file_name=f"{slugify(download_label)}.csv",
        mime="text/csv",
        key=f"download_{slugify(download_label)}",
    )


def render_insight_panels(df: pd.DataFrame) -> None:
    if df.empty:
        return

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Cadence mix")
        cadence_counts = (
            df["Frequency"].value_counts().rename_axis("Frequency").reset_index(name="Indicators")
        )
        if cadence_counts.empty:
            st.info("No cadence data available for this selection.")
        else:
            fig = px.bar(
                cadence_counts,
                x="Frequency",
                y="Indicators",
                color="Frequency",
                color_discrete_sequence=["#38bdf8", "#818cf8", "#22d3ee", "#f472b6"],
            )
            fig.update_traces(marker_line_width=0, opacity=0.92)
            style_fig(fig)
            render_plot(fig)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Framework alignment")
        alignment_records = []
        for framework in FRAMEWORK_COLUMNS:
            column = df[framework].fillna("No")
            yes_count = (column == "Yes").sum()
            some_count = (column == "Somewhat").sum()
            if yes_count:
                alignment_records.append({"Framework": framework, "Status": "Yes", "Indicators": yes_count})
            if some_count:
                alignment_records.append({"Framework": framework, "Status": "Somewhat", "Indicators": some_count})

        if not alignment_records:
            st.info("No framework signals for the current selection.")
        else:
            alignment_df = pd.DataFrame(alignment_records)
            fig = px.bar(
                alignment_df,
                x="Framework",
                y="Indicators",
                color="Status",
                barmode="stack",
                color_discrete_map={"Yes": "#34d399", "Somewhat": "#fbbf24"},
            )
            fig.update_traces(marker_line_width=0, opacity=0.95)
            style_fig(fig)
            render_plot(fig)
        st.markdown("</div>", unsafe_allow_html=True)

    domain_counts = (
        df["Domain"].value_counts().rename_axis("Domain").reset_index(name="Indicators")
    )
    if len(domain_counts) > 1:
        st.markdown("<div class='panel' style='margin-top: 1.5rem;'>", unsafe_allow_html=True)
        st.subheader("Domain coverage")
        fig = px.bar(
            domain_counts,
            x="Indicators",
            y="Domain",
            color="Domain",
            orientation="h",
            color_discrete_sequence=["#6366f1", "#14b8a6", "#f97316", "#f43f5e"],
        )
        fig.update_traces(marker_line_width=0, opacity=0.92)
        style_fig(fig)
        render_plot(fig)
        st.markdown("</div>", unsafe_allow_html=True)

def apply_filters(
    df: pd.DataFrame,
    *,
    search: str,
    domains: List[str],
    frequencies: List[str],
    granularities: List[str],
    frameworks: List[str],
) -> pd.DataFrame:
    filtered = df.copy()
    if search:
        pattern = search.lower()
        mask = (
            filtered["Indicator"].str.lower().str.contains(pattern, na=False)
            | filtered["Description"].str.lower().str.contains(pattern, na=False)
            | filtered["Domain"].str.lower().str.contains(pattern, na=False)
            | filtered["Section"].str.lower().str.contains(pattern, na=False)
        )
        filtered = filtered[mask]

    if domains:
        filtered = filtered[filtered["Domain"].isin(domains)]

    if frequencies:
        filtered = filtered[filtered["Frequency"].isin(frequencies)]

    if granularities:
        filtered = filtered[filtered["Granularity"].isin(granularities)]

    if frameworks:
        for fw in frameworks:
            filtered = filtered[filtered[fw].isin(["Yes", "Somewhat"])]

    return filtered.reset_index(drop=True)


def render_hero(stats: List[tuple[str, str]]) -> None:
    stats_html = "".join(
        f"<div class='hero-stat'><span class='label'>{html.escape(label)}</span><span class='value'>{html.escape(value)}</span></div>"
        for label, value in stats
    )

    st.markdown(
        f"""
        <div class='dashboard-hero'>
            <div class='hero-left'>
                <div class='hero-icon'>💧</div>
                <div>
                    <h1>Water &amp; Sanitation Utility Monitor</h1>
                    <p>Curated indicator catalogue aligned to global and regional frameworks.</p>
                </div>
            </div>
            <div class='hero-stats'>
                {stats_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_indicator_section(section_name: str, df: pd.DataFrame) -> None:
    st.markdown(f"#### {section_name}")
    st.caption(SECTION_DESCRIPTIONS.get(section_name, ""))

    section_df = df[df["Section"] == section_name]
    if section_df.empty:
        st.info("No indicators match the current filters for this section.")
        return

    render_insight_panels(section_df)

    ordered_subcats = SECTION_SUBCATEGORY_ORDER.get(section_name, [])
    available_subcats = [sub for sub in ordered_subcats if sub in section_df["Subcategory"].unique()]
    remaining_subcats = [
        sub for sub in section_df["Subcategory"].unique() if sub not in available_subcats
    ]
    subcategories = available_subcats + sorted(remaining_subcats)

    if len(subcategories) > 1:
        tabs = st.tabs(subcategories)
        for tab, sub in zip(tabs, subcategories):
            with tab:
                subset = section_df[section_df["Subcategory"] == sub]
                st.write(f"{len(subset)} indicator(s) • {', '.join(sorted(subset['Frequency'].unique()))}")
                display_indicator_table(subset, include_section=False, download_label=f"{section_name}_{sub}")
    else:
        sub = subcategories[0]
        subset = section_df[section_df["Subcategory"] == sub]
        st.write(f"{len(subset)} indicator(s) • {', '.join(sorted(subset['Frequency'].unique()))}")
        display_indicator_table(subset, include_section=False, download_label=f"{section_name}_{sub}")


def render_indicator_explorer(df: pd.DataFrame) -> None:
    st.markdown("#### Indicator Explorer")
    st.caption(SECTION_DESCRIPTIONS["Indicator Explorer"])

    if df.empty:
        st.info("No indicators match the current filters.")
        return

    summary = df.groupby("Section").size().sort_values(ascending=False)
    cols = st.columns(min(len(summary), 4))
    for col, (name, count) in zip(cols, summary.items()):
        col.metric(name, count)

    render_insight_panels(df)

    display_indicator_table(df, include_section=True, download_label="indicator_explorer")


def render_dashboard(with_page_config: bool = True):
    # Page config and styles for standalone use
    if with_page_config:
        st.set_page_config(
            page_title="Utility Performance Monitor",
            page_icon="💧",
            layout="wide",
        )
    _inject_base_styles()

    # --- Sidebar filters -------------------------------------------------
    st.sidebar.title("Filters")
    search_term = st.sidebar.text_input("Search indicators", placeholder="Search by indicator or description...")
    domain_filter = st.sidebar.multiselect("Domain", sorted(indicator_df["Domain"].unique()))
    frequency_filter = st.sidebar.multiselect("Frequency", sorted(indicator_df["Frequency"].unique()))
    granularity_filter = st.sidebar.multiselect("Granularity", sorted(indicator_df["Granularity"].unique()))
    framework_filter = st.sidebar.multiselect("Framework alignment", FRAMEWORK_COLUMNS)
    st.sidebar.caption("Framework filter keeps indicators where the selection is marked Yes or Somewhat.")

    filtered_df = apply_filters(
        indicator_df,
        search=search_term,
        domains=domain_filter,
        frequencies=frequency_filter,
        granularities=granularity_filter,
        frameworks=framework_filter,
    )

    total_count = len(filtered_df)
    annual_count = (filtered_df["Frequency"] == "Annual").sum()
    quarterly_count = (filtered_df["Frequency"] == "Quarterly").sum()
    monthly_count = (filtered_df["Frequency"] == "Monthly").sum()

    hero_stats = [
        ("Indicators", str(total_count)),
        ("Annual cadence", str(annual_count)),
        ("Quarterly cadence", str(quarterly_count)),
        ("Monthly cadence", str(monthly_count)),
    ]

    render_hero(hero_stats)

    # --- Section navigation as top tabs ---------------------------------
    section_tabs = st.tabs(SECTION_ORDER)
    for tab, section_name in zip(section_tabs, SECTION_ORDER):
        with tab:
            if section_name == "Indicator Explorer":
                render_indicator_explorer(filtered_df)
            else:
                render_indicator_section(section_name, filtered_df)

    st.markdown("---")
    st.markdown(
        "<p class='footer-note'>Mock data • Benchmarks: NRW<=25%, DWQ>=95%, Hours>=22, O&amp;M>=150%</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    render_dashboard(with_page_config=True)
