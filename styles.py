GLOBAL_STYLES = """<style>
    /* KLEIN BLUE & YELLOW THEME (High Contrast Pop Art) */
    @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
    
    /* 2. Main Window Container */
    .stApp {
        background-color: #002FA7 !important; /* Klein Blue */
        /* font-family: 'VT323', monospace !important;  <- Removed GLOBAL FORCE */
        color: #FFFFFF !important;
    }
    .stApp > header { display: none !important; }
    
    /* Apply VT323 to TEXT CONTAINERS only */
    div[class*="stMarkdown"], div[class*="stText"], p, h1, h2, h3, h4, h5, h6, input, button, label {
        font-family: 'VT323', monospace !important;
    }
    
    /* 2. Main Window Container */
    .stApp {
        background-color: #002FA7 !important; /* Klein Blue */
        color: #FFFFFF !important;
    }
    
    /* 1. Global Font Override (Aggressive & Complete) */
    * {
        font-family: 'VT323', monospace !important;
    }

    /* Exclude known icon classes and Sidebar Toggle */
    /* We MUST protect icons from the pixel font override, otherwise they show as text (e.g. "keyboard") */
    .material-icons, 
    .MuiSvgIcon-root, 
    [class*="MuiSvgIcon"], 
    [data-testid="stSidebarCollapseButton"] *, 
    [data-testid="stHeader"] button * {
        font-family: 'Material Icons', 'Material Symbols Rounded', sans-serif !important;
    }

    /* 5b. Pixel Search Icon */
    /* Target inputs that might be search bars (by context or generally apply to text inputs to look cool) */
    /* We hide the default SVG and add a background image */
    div[data-testid="stTextInput"] > div > div > svg {
        display: none !important;
    }
    
    /* Add pixel glass to sidebar inputs or specific search inputs */
    /* Using a simple 16x16 pixel art magnifying glass data URI */
    /* Add pixel glass to sidebar inputs or specific search inputs */
    /* REMOVED per user request to start standard */
    .stTextInput input {
        /* background-image: ...; REMOVED */
        padding-right: 10px !important;
    }
    
    /* 5. Inputs (High Contrast Universal) */
    .stTextInput div[data-baseweb="input"], 
    .stDateInput div[data-baseweb="input"], 
    .stTimeInput div[data-baseweb="input"], 
    .stNumberInput div[data-baseweb="input"], 
    .stSelectbox div[data-baseweb="select"], 
    .stMultiSelect div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #002FA7 !important; /* Blue Text */
        border: 2px solid #002FA7 !important;
        border-radius: 0px !important;
        box-shadow: 4px 4px 0px #F9DC24 !important;
    }
    
    }
    
    /* Inner Input Text Formatting */
    .stTextInput input, 
    .stDateInput input, 
    .stNumberInput input, 
    .stTimeInput input {
        color: #002FA7 !important; /* Blue Text */
        font-family: 'VT323', monospace !important;
        font-size: 20px !important;
    }

    /* Selectbox/Multiselect Text */
    .stSelectbox div[data-baseweb="select"] div,
    .stMultiSelect div[data-baseweb="select"] div {
         font-family: 'VT323', monospace !important;
         font-size: 20px !important;
         color: #002FA7 !important; /* Blue Text */
    }
    
    /* Adjust input text color for readability */
    input::placeholder {
        color: #002FA7 !important;
        opacity: 0.6;
    }

    /* Ensure Multiselect tags are visible */
    .stMultiSelect div[data-baseweb="tag"] {
        background-color: #F9DC24 !important;
        color: #002FA7 !important;
        border: 1px solid #002FA7 !important;
    }
    
    /* 6. Sidebar */
    /* 6. Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #F0F2F6 !important; /* Soft Grey/White - Less distracting */
        border-right: 2px solid #002FA7; /* Thin Blue Line instead of thick Yellow */
    }
    section[data-testid="stSidebar"] h2 {
        color: #002FA7 !important;
        border-bottom: none !important; /* Removed yellow line */
    }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label {
        color: #002FA7 !important; 
    }
    
    /* 7. Cards / Containers */
    .stat-card, .project-card {
        background: #FFFFFF;
        border: 2px solid #002FA7 !important;
        box-shadow: 6px 6px 0px 0px #F9DC24 !important; 
        border-radius: 0px !important;
        padding: 10px;
        margin-bottom: 20px;
    }

    /* 8. Bank Passbook Style (Retro Booklet) */
    .passbook-container {
        background-color: #F9DC24; /* Yellow Cover */
        border: 4px solid #002FA7; /* Blue Outline */
        border-left: 12px solid #D4AF37; /* Binding Spine (Darker) */
        border-radius: 0px 12px 12px 0px; /* Rounded textual edge */
        padding: 6px; 
        margin-bottom: 20px;
        box-shadow: 8px 8px 0px #002FA7;
        position: relative;
    }
    .passbook-inner-page {
        background: #FFFFFF;
        border: 2px solid #002FA7;
        padding: 10px;
        border-radius: 0px 8px 8px 0px;
        font-family: 'VT323', monospace;
        min-height: 120px;
    }
    .passbook-header {
        background: #002FA7 !important;
        color: #F9DC24 !important;
        font-weight: bold;
        text-align: center;
        border: 2px solid #F9DC24 !important;
        padding: 4px 0;
        font-size: 24px;
        text-transform: uppercase;
        margin-bottom: 10px;
        box-shadow: 0px 4px 0px rgba(0,0,0,0.1);
        transform: rotate(-1deg); /* Slight stamp effect */
    }
    
    /* Sidebar Modules (replacing st.container border) */
    .sidebar-module {
        background: #FFFFFF;
        border: 2px solid #002FA7;
        box-shadow: 4px 4px 0px #F9DC24; /* Yellow Shadow */
        padding: 12px;
        margin-bottom: 24px; /* Strong separation */
        position: relative;
    }
    .sidebar-module-title {
        background: #002FA7;
        color: #F9DC24;
        font-family: 'VT323', monospace;
        font-size: 18px;
        font-weight: bold;
        text-transform: uppercase;
        padding: 4px 8px;
        margin: -12px -12px 10px -12px; /* Full width edge-to-edge header */
        border-bottom: 2px solid #002FA7;
        letter-spacing: 1px;
    }
    
    .passbook-row {
        display: flex;
        flex-direction: column; /* Stack label and value for emphasis */
        align-items: center;    /* Center align */
        padding: 4px 8px;
        border-bottom: 2px dashed #002FA7; /* Stronger separation */
        margin-bottom: 5px;
    }
    .passbook-label {
        font-size: 14px;
        color: #002FA7 !important;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .passbook-large-val {
        font-family: 'VT323', monospace;
        font-size: 42px; /* HUGE */
        line-height: 1;
        font-weight: bold;
        color: #F9DC24 !important; /* Yellow Text FORCE */
        /* text-shadow removed as per user request */
    }
    .passbook-footer {
        font-size: 16px;
        color: #666;
        letter-spacing: 2px;
        margin-top: 5px;
        font-weight: bold;
        text-align: center;
        width: 100%;
        border-top: 1px dashed #002FA7;
        padding-top: 4px;
        text-transform: uppercase;
    }
    
    /* 9. Calendar Specifics */
    .fc { 
        background-color: #FFFFFF; 
        border: 4px solid #002FA7;
        font-family: 'VT323', monospace !important;
    }
    .fc-toolbar-title { font-size: 24px !important; color: #002FA7; text-transform: uppercase; }
    .fc-daygrid-day { border: 2px solid #002FA7 !important; }
    .fc-event {
        border: 2px solid #000 !important;
        border-radius: 0px !important;
        box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.2) !important;
        font-family: 'VT323', monospace !important;
        padding: 2px !important;
        font-weight: bold;
    }
    
    /* 9. Dialogs */
    div[data-testid="stDialog"] {
        background-color: #FFFFFF !important;
        border: 6px solid #F9DC24 !important;
        box-shadow: 15px 15px 0px #002FA7 !important;
        border-radius: 0px !important;
    }
    
    /* Utility */
    hr { border-color: #002FA7 !important; border-width: 2px; opacity: 0.2; border-style: solid; }
    
    /* 10. Sidebar Containers (The "Modules") */
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border: 2px solid #002FA7 !important;
        box-shadow: 4px 4px 0px #F9DC24 !important; /* Yellow Shadow */
        border-radius: 0px !important;
        margin-bottom: 24px !important;
        padding: 10px !important;
    }
    
    /* 11. Project Dashboard Grid */
    .stat-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 5px;
    }
    .stat-box {
        background: #F0F2F6; /* Light Grey */
        border: 2px solid #002FA7;
        padding: 8px 4px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 2px 2px 0px rgba(0,0,0,0.1);
    }
    .stat-num {
        font-family: 'VT323', monospace;
        font-size: 28px;
        font-weight: bold;
        line-height: 1;
        color: #002FA7;
    }
    .stat-label {
        font-family: 'VT323', monospace;
        font-size: 14px;
        color: #666;
        text-transform: uppercase;
        margin-top: 2px;
    }
    
    /* Ensure the internal container has no extra padding/gap issues */
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] > div {
        gap: 0.5rem;
    }

    /* Status Badge */
    .pixel-status-badge {
        font-family: 'VT323', monospace;
        font-size: 18px;
        font-weight: bold;
        padding: 4px 12px;
        border: 2px solid;
        text-transform: uppercase;
        display: inline-block;
        box-shadow: 2px 2px 0px rgba(0,0,0,0.1);
        background-color: #FFFFFF;
    }

    @media (prefers-color-scheme: dark) {
        /* Force Input Background to Light Gray in Dark Mode */
        div[data-baseweb="input"], 
        div[data-baseweb="select"], 
        .stTextInput input, 
        .stDateInput input, 
        .stTimeInput input, 
        .stNumberInput input,
        [data-testid="stTextInput"] input {
            background-color: #E2E8F0 !important;
            color: #002FA7 !important;
        }
        
        /* Lighten Project Details Dialog (Aggressive targeting) */
        div[data-testid="stDialog"] div[data-testid="stVerticalBlock"] {
            background-color: #F8FAFC !important; /* Extremely Light Gray */
            color: #1E293B !important;
            border: none !important;
            outline: none !important;
        }
        
        /* Ensure labels in dialog are dark blue/gray for contrast */
        div[data-testid="stDialog"] label, 
        div[data-testid="stDialog"] p,
        div[data-testid="stDialog"] div[data-testid="stMarkdownContainer"] p {
            color: #002FA7 !important;
        }

        /* Reform buttons inside dialog (Close button, Restore, etc) to match theme, NO BLACK */
        div[data-testid="stDialog"] button {
            border: 2px solid #002FA7 !important;
            color: #002FA7 !important;
            box-shadow: 2px 2px 0px #002FA7 !important;
            font-family: 'VT323', monospace !important;
            font-size: 16px !important;
            text-transform: uppercase !important;
            border-radius: 0px !important;
            transition: all 0.1s ease !important;
        }
        div[data-testid="stDialog"] button:hover {
            background-color: #002FA7 !important;
            color: #F9DC24 !important;
            border-color: #002FA7 !important;
            transform: translate(1px, 1px) !important;
            box-shadow: 1px 1px 0px #002FA7 !important;
        }

        /* Primary Buttons - Yellow accent - HIGH PRIORITY OVERRIDE */
        div[data-testid="stDialog"] button[kind="primary"],
        div[data-testid="stDialog"] button[data-testid="stBaseButton-primary"] {
            background-color: #F9DC24 !important;
            color: #002FA7 !important;
            border: 2px solid #002FA7 !important;
            box-shadow: 3px 3px 0px #000000 !important;
            font-weight: bold !important;
            min-height: 36px !important;
            height: auto !important;
            padding: 6px 16px !important;
            font-size: 16px !important;
        }
        div[data-testid="stDialog"] button[kind="primary"]:hover,
        div[data-testid="stDialog"] button[data-testid="stBaseButton-primary"]:hover {
            background-color: #002FA7 !important;
            color: #F9DC24 !important;
            box-shadow: 1px 1px 0px #000000 !important;
        }
        
        /* Prevent content overflow in dialog */
        div[data-testid="stDialog"] > div {
            overflow-x: hidden !important;
            max-width: 100% !important;
        }
        div[data-testid="stDialog"] div[data-testid="stVerticalBlock"] {
            max-width: 100% !important;
            overflow-x: hidden !important;
        }
        
        /* Recycle bin icon container in dialog - constrain size */
        div[data-testid="stDialog"] img {
            max-width: 50px !important;
            image-rendering: pixelated !important;
            background-color: transparent !important;
            border: none !important;
        }

        /* Multiselect Tags and Selectbox in Dialogs - FORCE LIGHT GRAY */
        div[data-testid="stDialog"] div[data-baseweb="select"],
        div[data-testid="stDialog"] div[data-baseweb="tag"],
        div[data-testid="stDialog"] div[data-baseweb="input"] {
            background-color: #E2E8F0 !important;
            color: #002FA7 !important;
            border-color: #002FA7 !important;
        }

        /* Target the actual dropdown menu (popover) */
        div[data-baseweb="popover"] div[role="listbox"],
        div[data-baseweb="popover"] div[data-baseweb="menu"] {
            background-color: #F8FAFC !important;
            color: #002FA7 !important;
        }
        
        div[data-baseweb="popover"] div[role="option"] {
            background-color: transparent !important;
            color: #002FA7 !important;
        }
        
        div[data-baseweb="popover"] div[role="option"]:hover {
            background-color: #F9DC24 !important;
            color: #000 !important;
        }
        
        /* multiselect tag text specifically */
        div[data-testid="stDialog"] div[data-baseweb="tag"] span {
            color: #002FA7 !important;
        }

        /* "Add" Buttons in Dialogs - FORCE LIGHT */
        div[data-testid="stDialog"] button[kind="secondary"] {
            background-color: #E2E8F0 !important;
            color: #002FA7 !important;
            border: 2px solid #002FA7 !important;
        }
        div[data-testid="stDialog"] button[kind="secondary"]:hover {
            background-color: #F9DC24 !important; /* Yellow hover */
            color: #000 !important;
        }
    }
</style>
"""
