import re
import os
import sys # Needed for QApplication
import pandas as pd
import geopandas as gpd
from typing import List, Dict, Any, Optional

# --- PySide6 Imports ---
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QTreeView, QLineEdit, QStatusBar, QMenuBar, QMessageBox,
    QSplitter, QLabel # QLabel for placeholder map/text areas
)
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction

# --- Matplotlib Imports (for future map display) ---
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.figure import Figure


# --- Configuration (保持不变) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MD_FILE_PATH = os.path.join(SCRIPT_DIR, "output.md")
MAPS_BASE_DIR = os.path.join(SCRIPT_DIR, "maps")

COUNTRY_SHP_PATH = os.path.join(MAPS_BASE_DIR, "1.Country", "country.shp")
PROVINCE_SHP_PATH = os.path.join(MAPS_BASE_DIR, "2.Province", "province.shp")
CITY_SHP_PATH = os.path.join(MAPS_BASE_DIR, "3.City", "city.shp")
DISTRICT_SHP_PATH = os.path.join(MAPS_BASE_DIR, "4.District", "district.shp")

# --- Regex (保持不变) ---
H1_MD_PATTERN = re.compile(r"^#\s+第[0-9]+章\s*(.+)$")
H2_SPECIAL_ZERO_PATTERN = re.compile(r"^##\s+零、上位类说明$")
H2_MD_PATTERN = re.compile(r"^##\s+(?:一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六|十七|十八|十九|二十|二十一|二十二|二十三|二十四|二十五|二十六|二十七|二十八|二十九|三十|三十一|三十二|三十三|三十四|三十五|三十六|三十七| ৩৮)、\s*(.+)$")
H3_SPECIAL_ZERO_PATTERN = re.compile(r"^###\s+0\.上位类说明$")
H3_MD_PATTERN = re.compile(r"^###\s*([1-9]|1[0-9]|2[0-5])\.\s*(.+)$") # Assuming your H3 MD Pattern is fine

AdministrativeRegion = Dict[str, Any]
ProcessedData = List[AdministrativeRegion]


# --- 数据处理函数 (parse_markdown, load_shapefiles, normalize_name, link_data, main_data_processing) ---
# (这里的代码与您V2.py中的版本保持一致，或者使用我们最后确认的版本)
# 为了简洁，我在这里省略这些函数的具体实现，假设它们在您的V2.py中是可用的
# 确保 link_data 函数在末尾返回 md_data

def parse_markdown(md_filepath: str) -> ProcessedData:
    # ... (您V2.py中的 parse_markdown 实现) ...
    # 确保此函数在失败时返回空列表 [] 或 None，并在成功时返回解析的数据
    # （根据上次日志，它能找到33个省份，所以是有效的）
    # 示例简化版 (实际应为完整版)
    print(f"Attempting to parse: {md_filepath}")
    # This is a highly simplified placeholder. Use your full parser.
    processed_data: ProcessedData = []
    current_province: Optional[AdministrativeRegion] = None
    current_city: Optional[AdministrativeRegion] = None
    current_text_buffer: List[str] = []
    current_collecting_for = "detail" # "prov_general", "city_general", "detail"

    def flush_buffer_to_entity(entity: Optional[AdministrativeRegion], field_name_override: Optional[str] = None):
        nonlocal current_collecting_for # Allow modification of outer scope variable
        if entity and current_text_buffer:
            actual_field_name = field_name_override if field_name_override else \
                                ("text_general" if "general" in current_collecting_for else "text_detail")
            
            if actual_field_name not in entity:
                entity[actual_field_name] = ""
            
            new_text = "\n".join(current_text_buffer).strip()
            if entity[actual_field_name] and new_text: # Add newline if appending to existing text
                 entity[actual_field_name] += "\n" + new_text
            elif new_text:
                 entity[actual_field_name] = new_text

            current_text_buffer.clear()

    try:
        with open(md_filepath, 'r', encoding='utf-8') as f:
            for line_content in f:
                line = line_content.strip()
                if not line: continue

                match_h1 = H1_MD_PATTERN.match(line)
                if match_h1:
                    flush_buffer_to_entity(current_city if current_city else current_province)
                    province_name = match_h1.group(1).strip()
                    current_province = {"name": province_name, "level": 1, "children": [], "text_detail": "", "text_general":""}
                    processed_data.append(current_province)
                    current_city = None
                    current_collecting_for = "detail" # Default for text after H1 but before ## 零...
                    continue

                if current_province and H2_SPECIAL_ZERO_PATTERN.match(line):
                    flush_buffer_to_entity(current_province, "text_detail") # Text before "## 零..." goes to prov detail
                    current_collecting_for = "prov_general"
                    continue
                
                match_h2 = H2_MD_PATTERN.match(line)
                if current_province and match_h2:
                    if current_city: # Flush previous city's text
                        flush_buffer_to_entity(current_city)
                    else: # Flush province's text (either general or detail)
                        flush_buffer_to_entity(current_province)

                    city_name = match_h2.group(1).strip()
                    current_city = {"name": city_name, "level": 2, "parent_name": current_province["name"], "children": [], "text_detail": "", "text_general":""}
                    current_province["children"].append(current_city)
                    current_collecting_for = "detail" # Default for text after H2 but before ### 0...
                    continue

                if current_city and H3_SPECIAL_ZERO_PATTERN.match(line):
                    flush_buffer_to_entity(current_city, "text_detail") # Text before "### 0..." goes to city detail
                    current_collecting_for = "city_general"
                    continue

                match_h3 = H3_MD_PATTERN.match(line)
                if current_city and match_h3:
                    flush_buffer_to_entity(current_city) # Flush previous text block
                    
                    h3_num_str = match_h3.group(1)
                    h3_name = match_h3.group(2).strip()
                    
                    # Create district object - IMPORTANT REFINEMENT
                    district_obj = {
                        "name": h3_name,
                        "num_str": h3_num_str, # Keep original numbering for now
                        "level": 3,
                        "parent_name": current_city["name"],
                        "text_detail": "" # Will collect text following this H3
                    }
                    if "children" not in current_city: # Should have been initialized
                        current_city["children"] = []
                    current_city["children"].append(district_obj)
                    current_collecting_for = "district_detail" # Now collecting for this district
                    # The current_text_buffer will now be flushed to district_obj["text_detail"]
                    # when the next H1, H2, H3, or special title is encountered, or EOF.
                    continue 
                
                # Accumulate text
                # The flush_buffer_to_entity needs to handle current_collecting_for="district_detail"
                # and flush to the last district in current_city['children'] if that's the case.
                # This is where the parser logic gets intricate.
                # For now, let's simplify: if it's collecting for district_detail, it needs to go to the LAST district.
                
                # A more robust flush_buffer_to_entity definition or state management
                # is needed to correctly assign text to the most recent district.
                # This simplified version will likely put all H3 text and subsequent general text
                # into the city or province due to the current flush logic.
                # THIS IS THE MAIN AREA FOR PARSER REFINEMENT.
                if current_collecting_for == "district_detail" and current_city and current_city["children"]:
                     # This text belongs to the last district added
                     # The flush logic needs to be aware of this state or receive the correct entity
                     # For simplicity, we append to buffer, flush will try to put it to city for now
                     pass # The current flush logic is too simple for this.

                current_text_buffer.append(line)

            # Final flush
            if current_collecting_for == "district_detail" and current_city and current_city["children"]:
                flush_buffer_to_entity(current_city["children"][-1], "text_detail")
            elif current_city:
                flush_buffer_to_entity(current_city)
            elif current_province:
                flush_buffer_to_entity(current_province)

    except FileNotFoundError:
        print(f"Error: Markdown file '{md_filepath}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred while parsing Markdown: {e}")
        import traceback
        traceback.print_exc()
        return []
    print(f"Markdown parsing. Found {len(processed_data)} provinces.")
    return processed_data

def load_shapefiles() -> Dict[str, gpd.GeoDataFrame]:
    # ... (您V2.py中的 load_shapefiles 实现) ...
    shapefiles = {}
    try:
        if os.path.exists(COUNTRY_SHP_PATH):
            shapefiles["country"] = gpd.read_file(COUNTRY_SHP_PATH)
        if os.path.exists(PROVINCE_SHP_PATH):
            shapefiles["province"] = gpd.read_file(PROVINCE_SHP_PATH)
        if os.path.exists(CITY_SHP_PATH):
            shapefiles["city"] = gpd.read_file(CITY_SHP_PATH)
        if os.path.exists(DISTRICT_SHP_PATH):
            shapefiles["district"] = gpd.read_file(DISTRICT_SHP_PATH)
    except Exception as e:
        print(f"Error loading shapefiles: {e}")
    return shapefiles


def normalize_name(name: str) -> str:
    # ... (您V2.py中的 normalize_name 实现, 建议加入去除后缀的逻辑如上次讨论) ...
    if name is None: return ""
    name = name.strip()
    suffixes_to_remove = ["省", "市", "区", "县", "自治州", "自治县", "地区", "盟"] 
    for suffix in suffixes_to_remove:
        if name.endswith(suffix) and len(name) > len(suffix): 
            name = name[:-len(suffix)]
            # break # only remove one suffix, usually the outermost one
    return name

def link_data(md_data: ProcessedData, shp_data: Dict[str, gpd.GeoDataFrame]) -> ProcessedData:
    # ... (您V2.py中最后确认的 link_data 实现) ...
    # 确保它在末尾返回 md_data
    print("--- Inside link_data ---")
    essential_shp_loaded_and_not_empty = (
        "province" in shp_data and shp_data["province"] is not None and not shp_data["province"].empty and
        "city" in shp_data and shp_data["city"] is not None and not shp_data["city"].empty and
        "district" in shp_data and shp_data["district"] is not None and not shp_data["district"].empty
    )
    if not md_data or not essential_shp_loaded_and_not_empty:
        print("Missing or empty data for linking. Aborting linking.")
        return md_data
    print("Preconditions PASSED. Proceeding with linking logic...")
    # ... (rest of linking logic from your V2.py, ensure it returns md_data at the end) ...
    gdf_provinces = shp_data["province"]
    gdf_cities = shp_data["city"]
    gdf_districts = shp_data["district"]

    for province_md in md_data:
        prov_name_md_original = province_md["name"]
        prov_name_md_normalized = normalize_name(prov_name_md_original)
        # ... (linking logic as in V2.py, with debug prints) ...
        # Ensure adcode and geometry are added to province_md, city_md
        if 'pr_name' not in gdf_provinces.columns: continue
        match_condition_series_prov = gdf_provinces['pr_name'].astype(str).apply(normalize_name) == prov_name_md_normalized
        matched_prov_shp = gdf_provinces[match_condition_series_prov]

        if not matched_prov_shp.empty:
            province_shp_row = matched_prov_shp.iloc[0]
            province_md["adcode"] = province_shp_row["pr_adcode"]
            province_md["geometry"] = province_shp_row.geometry
            # print(f"  SUCCESS: Linked Province: '{prov_name_md_normalized}' -> ADCODE {province_md['adcode']}")

            for city_md in province_md.get("children", []):
                city_name_md_original = city_md["name"]
                city_name_md_normalized = normalize_name(city_name_md_original)
                if 'ct_name' not in gdf_cities.columns or 'pr_adcode' not in gdf_cities.columns: continue
                
                potential_cities_shp = gdf_cities[gdf_cities['pr_adcode'] == province_md["adcode"]]
                match_condition_series_city = potential_cities_shp['ct_name'].astype(str).apply(normalize_name) == city_name_md_normalized
                matched_city_shp = potential_cities_shp[match_condition_series_city]

                if not matched_city_shp.empty:
                    city_shp_row = matched_city_shp.iloc[0]
                    city_md["adcode"] = city_shp_row["ct_adcode"]
                    city_md["geometry"] = city_shp_row.geometry
                    # print(f"      SUCCESS: Linked City: '{city_name_md_normalized}' -> ADCODE {city_md['adcode']}")
                    
                    # District linking (if district objects exist in city_md['children'])
                    for district_md in city_md.get("children", []): # Assuming districts are children of cities now
                        dist_name_md_original = district_md["name"]
                        dist_name_md_normalized = normalize_name(dist_name_md_original)
                        if 'dt_name' not in gdf_districts.columns or 'ct_adcode' not in gdf_districts.columns: continue

                        potential_districts_shp = gdf_districts[gdf_districts['ct_adcode'] == city_md["adcode"]]
                        match_condition_series_dist = potential_districts_shp['dt_name'].astype(str).apply(normalize_name) == dist_name_md_normalized
                        matched_district_shp = potential_districts_shp[match_condition_series_dist]

                        if not matched_district_shp.empty:
                            district_shp_row = matched_district_shp.iloc[0]
                            district_md["adcode"] = district_shp_row["dt_adcode"]
                            district_md["geometry"] = district_shp_row.geometry
                            # print(f"          SUCCESS: Linked District...")
                        # else:
                            # print(f"          WARNING: District '{dist_name_md_normalized}' not found...")
                # else:
                    # print(f"      WARNING: City '{city_name_md_normalized}' not found...")
        # else:
            # print(f"  WARNING: Province '{prov_name_md_normalized}' not found...")
    print("--- Data linking loop finished. ---")
    return md_data


def main_data_processing():
    # ... (您V2.py中的 main_data_processing 实现) ...
    print("--- Entering main_data_processing ---")
    print("--- Calling parse_markdown ---")
    parsed_md = parse_markdown(MD_FILE_PATH)
    print(f"--- Returned from parse_markdown. parsed_md is {'None or empty' if not parsed_md else 'Populated'} ---")
    if not parsed_md:
        print("Markdown parsing failed. Exiting.")
        return None
    print("--- Calling load_shapefiles ---")
    shapefile_data = load_shapefiles()
    print(f"--- Returned from load_shapefiles. shapefile_data keys: {list(shapefile_data.keys()) if shapefile_data else 'None or empty'} ---")
    required_shp_keys = ["country", "province", "city", "district"]
    missing_keys = [key for key in required_shp_keys if key not in shapefile_data or shapefile_data[key] is None or shapefile_data[key].empty]
    if missing_keys: # Check if any essential GDF is missing or empty
        print(f"Shapefile loading incomplete or essential shapefiles are empty. Missing/Empty keys: {missing_keys}. Exiting.")
        return None
    print("--- Calling link_data ---")
    linked_data_structure = link_data(parsed_md, shapefile_data)
    print("--- Returned from link_data ---")
    return linked_data_structure


# --- GUI Application Class ---
class MapViewer(QWidget):
    """Placeholder for the map display widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # In a real app, this would contain a Matplotlib canvas
        self.label = QLabel("地图显示区域\n(Country Map Placeholder)")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setMinimumSize(400, 300) # Give it some initial size

    def display_geometry(self, geometry_data: Optional[gpd.GeoSeries]):
        # TODO: Implement actual map plotting with Matplotlib/Geopandas
        if geometry_data is not None and not geometry_data.empty:
            # For now, just indicate which geometry *would* be displayed
            # In a real app:
            # self.ax.clear()
            # geometry_data.plot(ax=self.ax, ...)
            # self.canvas.draw()
            self.label.setText(f"地图应显示：\n{type(geometry_data)}\n(要素数量: {len(geometry_data) if hasattr(geometry_data, '__len__') else 'N/A'})")
        else:
            self.label.setText("地图显示区域\n(無有效地理數據)")

class MainWindow(QMainWindow):
    def __init__(self, data_store: Optional[ProcessedData], country_geom: Optional[gpd.GeoSeries]):
        super().__init__()
        self.data_store = data_store if data_store else [] # Store the processed data
        self.country_geometry = country_geom # Store country geometry separately for default view

        self.setWindowTitle("九域真形图 - 行政区沿革查询系统")
        self.setGeometry(100, 100, 1200, 800) # x, y, width, height

        self.init_ui()
        self.load_default_view()

    def init_ui(self):
        # --- Menu Bar ---
        menubar = self.menuBar()
        # File Menu (Optional, for future: Open, Exit)
        # file_menu = menubar.addMenu("文件")
        # exit_action = QAction("退出", self)
        # exit_action.triggered.connect(self.close)
        # file_menu.addAction(exit_action)

        browse_menu = menubar.addMenu("浏览")
        # browse_action = QAction("行政区列表", self) # Placeholder
        # browse_action.triggered.connect(self.show_browse_dialog_or_panel)
        # browse_menu.addAction(browse_action)
        # For now, browse might be a panel rather than dialog

        about_menu = menubar.addMenu("关于")
        about_action = QAction("关于九域真形图", self)
        about_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(about_action)

        # --- Central Widget and Layout ---
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget) # Main horizontal layout

        # Splitter for left and right panes
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Pane (Map + Future Browse Tree)
        left_pane_widget = QWidget()
        left_layout = QVBoxLayout(left_pane_widget)
        
        # TODO: Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入地名搜索 (至少2个汉字)...")
        # self.search_input.returnPressed.connect(self.perform_search)
        left_layout.addWidget(self.search_input)

        # TODO: Browse Tree (initially hidden or part of a tab)
        self.browse_tree = QTreeView()
        # self.populate_browse_tree() # Call this when browse is activated
        # left_layout.addWidget(self.browse_tree) # Add if always visible

        self.map_display_widget = MapViewer() # Our placeholder map widget
        left_layout.addWidget(self.map_display_widget, stretch=1) # Map takes available space

        splitter.addWidget(left_pane_widget)

        # Right Pane (Text Display)
        self.text_display_widget = QTextBrowser()
        self.text_display_widget.setOpenExternalLinks(True) # If MD is converted to HTML with links
        self.text_display_widget.setMinimumWidth(400)
        splitter.addWidget(self.text_display_widget)

        # Adjust initial sizes of splitter panes
        splitter.setSizes([600, 600]) # Initial even split, adjust as needed

        main_layout.addWidget(splitter)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪。")

    def load_default_view(self):
        """Loads the default country map and blank/welcome text."""
        if self.country_geometry is not None and not self.country_geometry.empty:
            self.map_display_widget.display_geometry(self.country_geometry)
        else:
            self.map_display_widget.display_geometry(None) # Show placeholder
            print("Warning: Country geometry not available for default view.")
        
        self.text_display_widget.setPlaceholderText("欢迎使用九域真形图。\n请通过浏览或搜索选择一个行政区以查看其沿革。")
        # Or set actual HTML/Text:
        # self.text_display_widget.setText("欢迎使用九域真形图。\n请通过浏览或搜索选择一个行政区以查看其沿革。")


    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "关于九域真形图",
            "九域真形图 - 各行政区沿革查询系统\n\n"
            "作者: Gemini 和 David Liu\n"
            f"数据最后处理时间: {str(pd.Timestamp.now(tz='Asia/Shanghai')) if pd else 'N/A'}" # Example of dynamic info
        )

    # --- Placeholder methods for other functionalities ---
    # def populate_browse_tree(self):
    #     # TODO: Populate self.browse_tree with self.data_store
    #     pass

    # def perform_search(self):
    #     # TODO: Implement search logic based on self.search_input.text()
    #     # Update map, text, and status bar
    #     query = self.search_input.text()
    #     if len(query) < 2:
    #         self.status_bar.showMessage("请输入至少两个汉字进行搜索。")
    #         return
    #     # ... search logic ...
    #     self.status_bar.showMessage(f"搜索 {query} ...")
    #     pass

    # def update_display_for_region(self, region_data: AdministrativeRegion):
    #     # TODO: Update map with region_data['geometry']
    #     # TODO: Update text with region_data text fields (convert MD to HTML if needed)
    #     self.map_display_widget.display_geometry(region_data.get("geometry"))
        
    #     text_to_display = f"<h1>{region_data.get('name', 'N/A')}</h1>"
    #     if region_data.get("text_general"):
    #         text_to_display += f"<h2>零/0. 上位类说明</h2><p>{region_data['text_general'].replace('\n', '<br>')}</p>"
    #     if region_data.get("text_detail"):
    #         text_to_display += f"<h2>详细沿革</h2><p>{region_data['text_detail'].replace('\n', '<br>')}</p>" # Basic HTML
    #     self.text_display_widget.setHtml(text_to_display) # If using HTML

    #     self.status_bar.showMessage(f"已显示: {region_data.get('name', 'N/A')}")
    #     pass


if __name__ == '__main__':
    print(f"Script directory: {SCRIPT_DIR}")
    print(f"Markdown file path: {MD_FILE_PATH}")
    print(f"Maps base directory: {MAPS_BASE_DIR}")

    final_data = main_data_processing() # This is your existing data processing pipeline

    country_geometry_data = None
    if final_data is not None: # Check if main_data_processing didn't fail
        # Attempt to get country geometry for default view
        # This assumes load_shapefiles() was successful and "country" key exists
        temp_shp_data = load_shapefiles() # Reload or ensure it's accessible
        if "country" in temp_shp_data and temp_shp_data["country"] is not None and not temp_shp_data["country"].empty:
            country_geometry_data = temp_shp_data["country"].geometry # Get the geometry series
            print("Country geometry loaded for default view.")
        else:
            print("Warning: Country shapefile not found or empty, default map will be placeholder.")

        # --- Launch GUI Application ---
        app = QApplication(sys.argv)
        window = MainWindow(final_data, country_geometry_data)
        window.show()
        sys.exit(app.exec())
    else:
        print("\nData processing failed or returned no data. GUI cannot be launched.")