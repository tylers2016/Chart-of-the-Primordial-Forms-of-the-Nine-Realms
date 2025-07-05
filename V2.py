import re
import os
import pandas as pd # To help with potential name matching or data structuring initially
import geopandas as gpd
from typing import List, Dict, Any, Optional

# --- Configuration ---
# Paths relative to the script location or an absolute path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Assumes script is in project root
MD_FILE_PATH = os.path.join(SCRIPT_DIR, "output.md")
MAPS_BASE_DIR = os.path.join(SCRIPT_DIR, "maps")

COUNTRY_SHP_PATH = os.path.join(MAPS_BASE_DIR, "1.Country", "country.shp")
PROVINCE_SHP_PATH = os.path.join(MAPS_BASE_DIR, "2.Province", "province.shp")
CITY_SHP_PATH = os.path.join(MAPS_BASE_DIR, "3.City", "city.shp")
DISTRICT_SHP_PATH = os.path.join(MAPS_BASE_DIR, "4.District", "district.shp")

# --- Regex for Markdown Parsing (from our previous discussion) ---
# H1: e.g., # 第5章 河北省
H1_MD_PATTERN = re.compile(r"^#\s+第[0-9]+章\s*(.+)$")
# H2 (Special): ## 零、上位类说明
H2_SPECIAL_ZERO_PATTERN = re.compile(r"^##\s+零、上位类说明$")
# H2 (Content): e.g., ## 一、石家庄市
H2_MD_PATTERN = re.compile(r"^##\s+(?:一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六|十七|十八|十九|二十|二十一|二十二|二十三|二十四|二十五|二十六|二十七|二十八|二十九|三十|三十一|三十二|三十三|三十四|三十五|三十六|三十七|三十八)、\s*(.+)$")
# H3 (Special): ### 0.上位类说明
H3_SPECIAL_ZERO_PATTERN = re.compile(r"^###\s+0\.上位类说明$")
# H3 (Content): e.g., ### 1.长安区 (allowing optional space after dot)
H3_MD_PATTERN = re.compile(r"^###\s*([1-9]|1[0-9]|2[0-5])\.\s*(.+)$")


# --- Data Structures (Conceptual, will be populated) ---
# Using dicts for now, can be classes later for more structure
# {
#   "adcode": "130000", 
#   "name": "河北省", 
#   "level": 1, 
#   "text_general": "...", 
#   "text_detail": "...", // Could be merged or specific
#   "geometry": <GeoPandas Geometry Object>,
#   "children": [ # for provinces, this would be cities; for cities, districts
#     { "adcode": "130100", "name": "石家庄市", ... }, ...
#   ]
# }
AdministrativeRegion = Dict[str, Any]
ProcessedData = List[AdministrativeRegion] # List of provinces


def parse_markdown(md_filepath: str) -> ProcessedData:
    """
    Parses the output.md file and extracts administrative regions and their descriptions.
    This is a complex part and will require careful state management.
    This initial version will be a simplified parser focusing on structure.
    """
    processed_data: ProcessedData = []
    current_province: Optional[AdministrativeRegion] = None
    current_city: Optional[AdministrativeRegion] = None
    # current_district: Optional[AdministrativeRegion] = None # Not strictly needed if H3 text goes to city

    # Buffer for collecting text for the current entity
    current_text_buffer: List[str] = []

    def flush_buffer_to_entity(entity: Optional[AdministrativeRegion], field_name: str = "text_detail"):
        if entity and current_text_buffer:
            # Ensure field exists and append, or create if not
            if field_name not in entity:
                entity[field_name] = ""
            # Append with space, clean up later if needed
            entity[field_name] += "\n".join(current_text_buffer).strip()
            current_text_buffer.clear()

    try:
        with open(md_filepath, 'r', encoding='utf-8') as f:
            for line_num, line_content in enumerate(f, 1):
                line = line_content.strip()
                if not line: # Skip empty lines
                    continue

                # Try matching H1 (Province)
                match_h1 = H1_MD_PATTERN.match(line)
                if match_h1:
                    flush_buffer_to_entity(current_city if current_city else current_province) # Flush previous entity's text
                    
                    province_name = match_h1.group(1).strip()
                    current_province = {
                        "name": province_name,
                        "level": 1,
                        "adcode": None, # To be filled by matching with shapefile
                        "text_general": "", # For "零、上位类说明"
                        "text_detail": "",  # For any direct province description before cities
                        "geometry": None,
                        "children": [] # Cities
                    }
                    processed_data.append(current_province)
                    current_city = None # Reset city context
                    continue

                # Try matching H2 Special (Province General Description)
                if current_province and H2_SPECIAL_ZERO_PATTERN.match(line):
                    flush_buffer_to_entity(current_province, "text_detail") # Flush any preceding text for province
                    # Next lines will be part of text_general for province
                    # To keep it simple, we'll have a specific state or directly assign
                    # For now, assume text that follows belongs to this
                    # This part of parsing "which text belongs to where" is tricky
                    # We can refine this: a state variable like "collecting_for_province_general"
                    continue # The H2 title itself is not text content

                # Try matching H2 (City)
                match_h2 = H2_MD_PATTERN.match(line)
                if current_province and match_h2:
                    flush_buffer_to_entity(current_city if current_city else current_province) # Flush previous entity's text

                    city_name = match_h2.group(1).strip()
                    current_city = {
                        "name": city_name,
                        "level": 2,
                        "parent_adcode": current_province.get("adcode"), # If province adcode is known
                        "parent_name": current_province["name"],
                        "adcode": None,
                        "text_general": "", # For "0.上位类说明"
                        "text_detail": "", # For city specific desc / H3 texts
                        "geometry": None,
                        "children": [] # Districts
                    }
                    current_province["children"].append(current_city)
                    continue
                
                # Try matching H3 Special (City General Description)
                if current_city and H3_SPECIAL_ZERO_PATTERN.match(line):
                    flush_buffer_to_entity(current_city, "text_detail") # Flush any preceding text for city
                    # Similar to H2_SPECIAL_ZERO, text that follows belongs to this.
                    # A state like "collecting_for_city_general" could be used.
                    continue

                # Try matching H3 (District/County)
                match_h3 = H3_MD_PATTERN.match(line)
                if current_city and match_h3:
                    flush_buffer_to_entity(current_city, "text_detail") # Flush previous text block which might belong to city or previous H3

                    h3_num_str = match_h3.group(1)
                    h3_name = match_h3.group(2).strip()
                    
                    # For simplicity now, H3 text will be aggregated under the parent city's "text_detail"
                    # A more complex model would have district objects.
                    # Let's start by appending H3 title and its subsequent text to city's detail.
                    # This needs refinement for "search by district" and "display district map"
                    current_text_buffer.append(f"### {h3_num_str}.{h3_name}") # Add the H3 title itself
                    # Subsequent non-title lines will be added to current_text_buffer
                    continue

                # If none of the above, it's content text
                current_text_buffer.append(line)
            
            # Flush any remaining buffer at the end of the file
            flush_buffer_to_entity(current_city if current_city else current_province)

    except FileNotFoundError:
        print(f"Error: Markdown file '{md_filepath}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred while parsing Markdown: {e}")
        return []
        
    # Refinement for "零、上位类说明" and "0.上位类说明" text assignment
    # The current simple flush_buffer might not assign these correctly.
    # A proper state machine is needed for perfect assignment.
    # E.g., after ## 零..., set state to "collect_prov_general".
    # After ### 0..., set state to "collect_city_general".
    # When another structural title appears, flush to the correct field based on state.

    # For this first pass, the text might be mostly in "text_detail".
    # We will need to refine how 'text_general' for province/city is populated
    # from the text following "## 零..." and "### 0..." respectively.

    # Placeholder for refinement:
    # Let's assume for now that a block of text after "## 零..." belongs to current_province["text_general"]
    # and after "### 0..." belongs to current_city["text_general"].
    # The current_text_buffer logic needs to be smarter about *where* it flushes.

    # TODO: Refine text assignment logic for "零、上位类说明" and "0.上位类说明"
    # A simple way for now for demonstration:
    # Iterate through processed_data, if a province has children (cities),
    # the text directly under province (before first city) is its detail.
    # The text directly under city (before first district H3) is its detail.
    # H3 text is added to its parent city's detail.

    # This parser is a STARTING POINT and needs significant refinement for accurate text categorization.
    print(f"Markdown parsing (initial pass) complete. Found {len(processed_data)} provinces.")
    return processed_data


def load_shapefiles() -> Dict[str, gpd.GeoDataFrame]:
    """Loads all necessary shapefiles."""
    shapefiles = {}
    try:
        print("Loading country.shp...")
        shapefiles["country"] = gpd.read_file(COUNTRY_SHP_PATH)
        print(f"Loaded country.shp: {len(shapefiles['country'])} features. Columns: {shapefiles['country'].columns.tolist()}")
        
        print("Loading province.shp...")
        shapefiles["province"] = gpd.read_file(PROVINCE_SHP_PATH)
        print(f"Loaded province.shp: {len(shapefiles['province'])} features. Columns: {shapefiles['province'].columns.tolist()}")

        print("Loading city.shp...")
        shapefiles["city"] = gpd.read_file(CITY_SHP_PATH)
        print(f"Loaded city.shp: {len(shapefiles['city'])} features. Columns: {shapefiles['city'].columns.tolist()}")

        print("Loading district.shp...")
        shapefiles["district"] = gpd.read_file(DISTRICT_SHP_PATH)
        print(f"Loaded district.shp: {len(shapefiles['district'])} features. Columns: {shapefiles['district'].columns.tolist()}")
        
        print("Shapefile loading complete.")
    except Exception as e:
        print(f"Error loading shapefiles: {e}")
        # Potentially return partially loaded dict or raise error
    return shapefiles


def normalize_name(name: str) -> str:
    """Normalizes administrative names for matching."""
    if name is None: return ""
    name = name.strip()
    # Remove common suffixes for broader matching if necessary, but exact match first
    # suffixes_to_remove = ["省", "市", "区", "县", "自治州", "自治县", "地区"] # Example
    # for suffix in suffixes_to_remove:
    #     if name.endswith(suffix):
    #         name = name[:-len(suffix)]
    #         break
    return name


def link_data(md_data: ProcessedData, shp_data: Dict[str, gpd.GeoDataFrame]) -> ProcessedData:
    """
    Links the parsed Markdown data with Shapefile data, primarily using adcodes
    obtained via name matching.
    This function will populate 'adcode' and 'geometry' in the md_data structure.
    """
    print("--- Inside link_data ---")

    # Simplified and effective precondition check
    essential_shp_loaded_and_not_empty = (
        "province" in shp_data and shp_data["province"] is not None and not shp_data["province"].empty and
        "city" in shp_data and shp_data["city"] is not None and not shp_data["city"].empty and
        "district" in shp_data and shp_data["district"] is not None and not shp_data["district"].empty
    )

    if not md_data or not essential_shp_loaded_and_not_empty:
        print("Missing or empty data for linking (md_data or essential shapefiles). Aborting linking.")
        # It's important to return md_data so main_data_processing doesn't get None
        # if only shapefiles were the issue but md_data was parsed.
        # Or, if this is a critical failure, consider raising an exception or returning None
        # and handling it in main_data_processing. For now, returning md_data.
        return md_data

    print("Preconditions PASSED. Proceeding with linking logic...")

    gdf_provinces = shp_data["province"]
    gdf_cities = shp_data["city"]
    gdf_districts = shp_data["district"] # Keep for future district-level linking

    for province_md in md_data:
        prov_name_md_normalized = normalize_name(province_md["name"])
        print(f"\nProcessing MD Province: '{prov_name_md_normalized}' (Original from MD: '{province_md['name']}')")

        # Match province by normalized name
        # Ensure 'pr_name' column exists and handle potential missing values if any
        if 'pr_name' not in gdf_provinces.columns:
            print(f"  ERROR: 'pr_name' column not found in province shapefile. Skipping province '{prov_name_md_normalized}'.")
            continue
        
        # Ensure names in GeoDataFrame are strings before applying normalize_name
        # gdf_provinces['pr_name'].fillna('', inplace=True) # Handle potential NaN values by replacing with empty string
        
        match_condition_series_prov = gdf_provinces['pr_name'].astype(str).apply(normalize_name) == prov_name_md_normalized
        matched_prov_shp = gdf_provinces[match_condition_series_prov]
        
        print(f"  Trying to match '{prov_name_md_normalized}'. Found in shapefile? {'Yes' if not matched_prov_shp.empty else 'No'}. Matched count: {len(matched_prov_shp)}")

        if not matched_prov_shp.empty:
            # Take the first match if multiple (though adcode/name should be unique for provinces)
            province_shp_row = matched_prov_shp.iloc[0]
            province_md["adcode"] = province_shp_row["pr_adcode"]
            province_md["geometry"] = province_shp_row.geometry
            print(f"  Linked Province: '{prov_name_md_normalized}' -> ADCODE {province_md['adcode']}")

            for city_md in province_md.get("children", []): # Use .get for safety
                city_name_md_normalized = normalize_name(city_md["name"])
                print(f"    Processing MD City: '{city_name_md_normalized}' (Original from MD: '{city_md['name']}') under Province '{prov_name_md_normalized}'")

                if 'ct_name' not in gdf_cities.columns or 'pr_adcode' not in gdf_cities.columns:
                    print(f"      ERROR: 'ct_name' or 'pr_adcode' column not found in city shapefile. Skipping city '{city_name_md_normalized}'.")
                    continue
                
                # gdf_cities['ct_name'].fillna('', inplace=True) # Handle NaN

                # Filter cities belonging to the current matched province
                potential_cities_shp = gdf_cities[gdf_cities['pr_adcode'] == province_md["adcode"]]
                
                match_condition_series_city = potential_cities_shp['ct_name'].astype(str).apply(normalize_name) == city_name_md_normalized
                matched_city_shp = potential_cities_shp[match_condition_series_city]
                
                print(f"      Trying to match '{city_name_md_normalized}'. Found in shapefile (within province {province_md['adcode']})? {'Yes' if not matched_city_shp.empty else 'No'}. Matched count: {len(matched_city_shp)}")

                if not matched_city_shp.empty:
                    city_shp_row = matched_city_shp.iloc[0]
                    city_md["adcode"] = city_shp_row["ct_adcode"]
                    city_md["geometry"] = city_shp_row.geometry
                    # city_md["parent_adcode"] = province_md["adcode"] # Already set during parsing potentially, or confirm here
                    print(f"      Linked City: '{city_name_md_normalized}' -> ADCODE {city_md['adcode']}")

                    # Placeholder for District Linking (if district_md objects are created by parser)
                    # for district_md in city_md.get("children", []):
                    #     dist_name_md_normalized = normalize_name(district_md["name"])
                    #     print(f"        Processing MD District: '{dist_name_md_normalized}' under City '{city_name_md_normalized}'")
                    #     if 'dt_name' not in gdf_districts.columns or 'ct_adcode' not in gdf_districts.columns:
                    #         print(f"          ERROR: 'dt_name' or 'ct_adcode' column not found in district shapefile. Skipping.")
                    #         continue
                        
                    #     potential_districts_shp = gdf_districts[gdf_districts['ct_adcode'] == city_md["adcode"]]
                    #     match_condition_series_dist = potential_districts_shp['dt_name'].astype(str).apply(normalize_name) == dist_name_md_normalized
                    #     matched_district_shp = potential_districts_shp[match_condition_series_dist]

                    #     if not matched_district_shp.empty:
                    #         district_shp_row = matched_district_shp.iloc[0]
                    #         district_md["adcode"] = district_shp_row["dt_adcode"]
                    #         district_md["geometry"] = district_shp_row.geometry
                    #         print(f"          Linked District: '{dist_name_md_normalized}' -> ADCODE {district_md['adcode']}")
                    #     else:
                    #         print(f"          WARNING: District '{dist_name_md_normalized}' not found in shapefile under City ADCODE {city_md.get('adcode')}.")
                else:
                    print(f"      WARNING: City '{city_name_md_normalized}' not found in shapefile under Province '{prov_name_md_normalized}' (ADCODE {province_md.get('adcode')}).")
        else:
            print(f"  WARNING: Province '{prov_name_md_normalized}' not found in shapefile.")
    
    print("--- Data linking loop finished. ---")
    return md_data


def main_data_processing():
    """Main function to orchestrate data loading, parsing, and linking."""
    print("--- Entering main_data_processing ---") # <--- 新增：确认函数被调用

    # 1. Parse Markdown
    print("--- Calling parse_markdown ---") # <--- 新增
    parsed_md = parse_markdown(MD_FILE_PATH)
    print(f"--- Returned from parse_markdown. parsed_md is {'None or empty' if not parsed_md else 'Populated'} ---") # <--- 新增

    if not parsed_md:
        print("Markdown parsing failed or returned no data. Exiting main_data_processing.") # <--- 新增更明确的退出信息
        return None

    # 2. Load Shapefiles
    print("--- Calling load_shapefiles ---") # <--- 新增
    shapefile_data = load_shapefiles()
    print(f"--- Returned from load_shapefiles. shapefile_data keys: {list(shapefile_data.keys()) if shapefile_data else 'None or empty'} ---") # <--- 新增

    # Check if all essential shapefiles were loaded into the dictionary
    required_shp_keys = ["country", "province", "city", "district"]
    missing_keys = [key for key in required_shp_keys if key not in shapefile_data]

    if missing_keys:
        print(f"Shapefile loading incomplete. Missing keys: {missing_keys}. Exiting main_data_processing.") # <--- 新增更明确的退出信息
        return None # Or handle as an error state preventing linking

    # 3. Link Markdown Data with Shapefile Data
    print("--- Calling link_data ---") # <--- 新增
    linked_data_structure = link_data(parsed_md, shapefile_data)
    print("--- Returned from link_data ---") # <--- 新增

    return linked_data_structure


# --- Placeholder for GUI Application ---
# This will be in a separate, much larger section of code.
# from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QTreeView, QLineEdit, QStatusBar, QMenuBar
# from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
# from PySide6.QtGui import QStandardItemModel, QStandardItem
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

# class MainWindow(QMainWindow):
#     def __init__(self, data_store):
#         super().__init__()
#         self.data_store = data_store # This will be the linked_data_structure
#         self.setWindowTitle("九域真形图 - 行政区沿革查询系统")
#         self.setGeometry(100, 100, 1200, 800)
        
#         # ... rest of GUI setup ...
#         self.init_ui()

#     def init_ui(self):
#         # Menu Bar
#         menubar = self.menuBar()
#         browse_menu = menubar.addMenu("浏览")
#         # browse_action = browse_menu.addAction("行政区列表") # Will trigger tree view population
#         # browse_action.triggered.connect(self.populate_browse_tree)
        
#         about_menu = menubar.addMenu("关于")
#         about_action = about_menu.addAction("关于九域真形图")
#         about_action.triggered.connect(self.show_about_dialog)

        # Main widget and layout
        # ... (Splitter for left (map) and right (text) panes)
        # ... (Search bar, status bar)
        # ... (Map canvas, text browser, tree view for Browse)
        
        # Default view
        # self.display_country_map() # Placeholder
        # self.status_bar = QStatusBar()
        # self.setStatusBar(self.status_bar)
        # self.status_bar.showMessage("就绪。")
        # pass

    # def display_country_map(self):
    #     # ... logic to plot country.shp ...
    #     pass

    # def show_about_dialog(self):
    #     # QMessageBox.about(self, "关于九域真形图", "九域真形图\n作者: Gemini 和 David Liu")
    #     pass
        
    # # ... other methods for search, browse selection, map update, text update ...


if __name__ == '__main__':
    print(f"Script directory: {SCRIPT_DIR}")
    print(f"Markdown file path: {MD_FILE_PATH}")
    print(f"Maps base directory: {MAPS_BASE_DIR}")

    # --- This is the entry point for data processing ---
    # The GUI part would be instantiated after this if data is successfully processed
    final_data = main_data_processing()

    if final_data:
        print("\nData processing finished. Structure is ready for GUI.")
        print(f"Total provinces processed and linked (top level): {len(final_data)}")
        # To run GUI (example, actual GUI code is extensive and not fully written here):
        # app = QApplication([])
        # window = MainWindow(final_data)
        # window.show()
        # app.exec()
    else:
        print("\nData processing failed. GUI cannot be launched.")