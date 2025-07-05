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

# ... (保持之前的 imports 不变，确保以下 matplotlib 和 PySide6 相关导入存在)
import sys
import geopandas as gpd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QTreeView, QLineEdit, QStatusBar, QMenuBar, QMessageBox,
    QSplitter, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem # Ensure QStandardItem related imports are here

# Matplotlib imports for embedding in PySide6
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt # Usually good to have for colormaps etc. later

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
    """Widget to display maps using Matplotlib and Geopandas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(5, 5)) # Create a Matplotlib Figure
        self.canvas = FigureCanvas(self.figure) # Create a canvas for the figure
        self.ax = self.figure.add_subplot(111) # Add an Axes to the figure

        # Basic plot styling (optional, can be expanded)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)
        self.ax.spines['left'].set_visible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas) # Add the canvas to the layout
        self.setMinimumSize(400, 300)

    def display_geometry(self, geometry_data: Optional[gpd.GeoDataFrame | gpd.GeoSeries], fit_bounds=True):
        """Clears current plot and displays new geometry data."""
        self.ax.clear() # Clear the previous plot

        if geometry_data is not None and not geometry_data.empty:
            try:
                # If it's a GeoDataFrame, plot directly. If GeoSeries, it's also plottable.
                geometry_data.plot(ax=self.ax, edgecolor='black', color='lightblue') # Basic styling
                
                if fit_bounds:
                    # Calculate bounds and set limits to zoom to the geometry
                    minx, miny, maxx, maxy = geometry_data.total_bounds
                    # Add some padding to the bounds
                    padding_x = (maxx - minx) * 0.1
                    padding_y = (maxy - miny) * 0.1
                    self.ax.set_xlim(minx - padding_x, maxx + padding_x)
                    self.ax.set_ylim(miny - padding_y, maxy + padding_y)
                
                self.ax.set_aspect('equal', adjustable='box') # Ensure correct aspect ratio
            except Exception as e:
                print(f"Error plotting geometry: {e}")
                self.ax.text(0.5, 0.5, "无法绘制地图数据", ha='center', va='center')
        else:
            self.ax.text(0.5, 0.5, "无有效地理数据可显示", ha='center', va='center')
        
        # Redraw basic plot styling if cleared
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        
        self.canvas.draw() # Redraw the canvas

class MainWindow(QMainWindow):
    def __init__(self, data_store: Optional[ProcessedData], country_gdf: Optional[gpd.GeoDataFrame]):
        super().__init__()
        self.data_store = data_store if data_store else []
        self.country_geodataframe = country_gdf

        self.setWindowTitle("九域真形图 - 行政区沿革查询系统")
        self.setGeometry(100, 100, 1280, 820) # 稍微调整了尺寸

        self.init_ui()
        self.load_default_view()
        if self.data_store: # Populate browse tree if data is available
            self.populate_browse_tree()

    def init_ui(self):
        # --- Menu Bar ---
        menubar = self.menuBar()
        browse_menu = menubar.addMenu("浏览")
        # We will use the tree view directly, so a separate action might not be needed
        # unless you want to toggle its visibility.

        about_menu = menubar.addMenu("关于")
        about_action = QAction("关于九域真形图", self)
        about_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(about_action)

        # --- Central Widget and Layout ---
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter_main = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Pane ---
        left_pane_widget = QWidget()
        left_layout = QVBoxLayout(left_pane_widget)
        left_layout.setContentsMargins(0,0,0,0) # Remove margins for tighter packing

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入地名搜索 (至少2个汉字)...")
        self.search_input.returnPressed.connect(self.perform_search) # Connect search
        left_layout.addWidget(self.search_input)

        # --- Browse Tree ---
        self.browse_tree = QTreeView()
        self.browse_tree.setHeaderHidden(True) # Hide the default header
        self.tree_model = QStandardItemModel()
        self.browse_tree.setModel(self.tree_model)
        self.browse_tree.clicked[QModelIndex].connect(self.on_browse_item_selected)
        
        # Splitter for search/browse and map (within left pane)
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.addWidget(self.browse_tree) # Add browse tree here

        self.map_display_widget = MapViewer()
        left_splitter.addWidget(self.map_display_widget)
        left_splitter.setSizes([200, 400]) # Initial size for browse tree and map

        left_layout.addWidget(left_splitter)
        
        splitter_main.addWidget(left_pane_widget)

        # --- Right Pane (Text Display) ---
        self.text_display_widget = QTextBrowser()
        self.text_display_widget.setOpenExternalLinks(True)
        self.text_display_widget.setMinimumWidth(400)
        splitter_main.addWidget(self.text_display_widget)

        splitter_main.setSizes([450, 800]) # Initial size for left and right panes
        main_layout.addWidget(splitter_main)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪。")

    def load_default_view(self):
        if self.country_geodataframe is not None and not self.country_geodataframe.empty:
            self.map_display_widget.display_geometry(self.country_geodataframe)
        else:
            self.map_display_widget.display_geometry(None)
            print("Warning: Country GeoDataFrame not available for default view.")
        self.text_display_widget.setHtml("<h1>欢迎使用九域真形图</h1><p>请通过浏览或搜索选择一个行政区以查看其沿革。</p>")

    def populate_browse_tree(self):
        self.tree_model.clear() # Clear previous items
        # Add a root item if you want a single top-level entry, or directly add provinces
        # root_item = self.tree_model.invisibleRootItem()

        for province_data in self.data_store:
            prov_name = province_data.get('name', '未知省份')
            prov_item = QStandardItem(prov_name)
            prov_item.setData(province_data, Qt.ItemDataRole.UserRole) # Store the whole dict
            prov_item.setEditable(False)
            # root_item.appendRow(prov_item) # If using a single root
            self.tree_model.appendRow(prov_item)


            for city_data in province_data.get("children", []):
                city_name = city_data.get('name', '未知城市')
                city_item = QStandardItem(city_name)
                city_item.setData(city_data, Qt.ItemDataRole.UserRole)
                city_item.setEditable(False)
                prov_item.appendRow(city_item)

                # Assuming 'children' of city are districts
                for district_data in city_data.get("children", []):
                    dist_name = district_data.get('name', '未知区县')
                    # If your H3 parsing includes num_str: f"{district_data.get('num_str', '')}. {dist_name}"
                    dist_display_name = dist_name 
                    dist_item = QStandardItem(dist_display_name)
                    dist_item.setData(district_data, Qt.ItemDataRole.UserRole)
                    dist_item.setEditable(False)
                    city_item.appendRow(dist_item)
        print("Browse tree populated.")

    def on_browse_item_selected(self, index: QModelIndex):
        item = self.tree_model.itemFromIndex(index)
        if item:
            region_data = item.data(Qt.ItemDataRole.UserRole)
            if region_data and isinstance(region_data, dict):
                print(f"Browse selected: {region_data.get('name')}, Level: {region_data.get('level')}")
                self.update_display_for_region(region_data)
            else:
                print(f"Browse selection error: No data or incorrect data type for item '{item.text()}'")


    def update_display_for_region(self, region_data: Optional[AdministrativeRegion]):
        """Updates map and text display for the selected region."""
        if region_data and isinstance(region_data, dict):
            self.map_display_widget.display_geometry(region_data.get("geometry")) # Expects GeoDataFrame or GeoSeries

            name_display = region_data.get('name', '未知区域')
            level_map = {1: "省/直辖市/自治区", 2: "市/地区/自治州", 3: "区/县/县级市"}
            level_text = level_map.get(region_data.get("level"), "未知级别")
            
            html_content = f"<h1>{name_display} <small>({level_text})</small></h1>"
            if region_data.get("adcode"):
                html_content += f"<p><b>行政代码:</b> {region_data['adcode']}</p>"

            # Prioritize specific general texts if they exist
            text_general = region_data.get("text_general", "")
            text_detail = region_data.get("text_detail", "")
            
            # Simple conversion of newlines to <br> for now
            # For full markdown, use a library: e.g., markdown.markdown(text)
            # Need to handle potential None or empty strings gracefully
            def format_text_block(text: Optional[str]) -> str:
                if not text:
                    return ""
                # Basic Markdown-like paragraph separation (double newline) to <p>
                paragraphs = re.split(r'\n\s*\n', text.strip())
                html_paragraphs = ["<p>" + p.replace('\n', '<br>') + "</p>" for p in paragraphs if p.strip()]
                return "".join(html_paragraphs)


            if text_general: # Text from "零./0. 上位类说明"
                html_content += f"<h2>上位类说明</h2><div>{format_text_block(text_general)}</div>"
            
            if text_detail: # Main body of text
                # Check if text_detail already contains H3 titles from parsing (current simple parser does this)
                # If so, we might want to render them as H3 in HTML too.
                # For now, just format as block.
                html_content += f"<h2>详细沿革</h2><div>{format_text_block(text_detail)}</div>"
            
            self.text_display_widget.setHtml(html_content)
            self.status_bar.showMessage(f"已显示: {name_display}")
        else:
            self.text_display_widget.setHtml("<p>未选择区域或无有效数据。</p>")
            # self.map_display_widget.display_geometry(None) # Optionally clear map or show country
            if self.country_geodataframe is not None: # Revert to country map if no region selected
                 self.map_display_widget.display_geometry(self.country_geodataframe)
            else:
                 self.map_display_widget.display_geometry(None)
            self.status_bar.showMessage("请选择一个区域。")

    def perform_search(self):
        query = self.search_input.text().strip()
        if len(query) < 2:
            self.status_bar.showMessage("请输入至少两个汉字进行搜索。")
            return

        self.status_bar.showMessage(f"正在搜索: '{query}'...")
        found_regions = []
        # Iterate through the data_store to find matches
        # This is a simple search, can be optimized for larger datasets
        
        # Helper for recursive search
        def search_recursive(regions_list: List[AdministrativeRegion]):
            for region in regions_list:
                region_name = region.get("name", "")
                # Exact match or partial match (query in name, or name in query for short queries)
                if query == region_name or query in region_name or region_name in query:
                    found_regions.append(region)
                
                if "children" in region:
                    search_recursive(region["children"])

        search_recursive(self.data_store)

        if found_regions:
            # "默认选中第一个（就是md文档中匹配的第一个）"
            # Our self.data_store is built in MD order, so found_regions[0] is fine.
            selected_region = found_regions[0]
            self.update_display_for_region(selected_region)
            self.status_bar.showMessage(f"找到 {len(found_regions)} 个相关区域。已显示: {selected_region.get('name', '')}")
            
            # Optionally, expand and select in browse_tree if item exists
            # This is more complex: requires finding the QStandardItem for selected_region['adcode']
            # self.select_item_in_tree(selected_region.get('adcode'))
        else:
            self.status_bar.showMessage(f"未找到与 '{query}' 相关的区域。")
            # self.update_display_for_region(None) # Clear display or show default


    def show_about_dialog(self): # (保持不变)
        QMessageBox.about(
            self,
            "关于九域真形图",
            "九域真形图 - 各行政区沿革查询系统\n\n"
            "作者: Gemini 和 David Liu\n"
            f"版本: 0.2 (Browse Alpha)\n"
        )
    
    # def update_display_for_region(self, region_data: AdministrativeRegion):
    #     """Updates map and text display for the selected region."""
    #     if region_data:
    #         self.map_display_widget.display_geometry(region_data.get("geometry")) # Assuming geometry is GeoSeries/GeoDataFrame
            
    #         # --- Prepare text content ---
    #         # This part will need the markdown to HTML conversion eventually
    #         name_display = region_data.get('name', '未知区域')
    #         level_map = {1: "省份", 2: "市", 3: "区县"}
    #         level_text = level_map.get(region_data.get("level"), "未知级别")
            
    #         html_content = f"<h1>{name_display} ({level_text})</h1>"
    #         if region_data.get("adcode"):
    #             html_content += f"<p><b>行政代码:</b> {region_data['adcode']}</p>"

    #         general_desc = region_data.get("text_general", "")
    #         detail_desc = region_data.get("text_detail", "")

    #         if general_desc:
    #             # Basic conversion of newlines to <br> for now
    #             # For full markdown, use a library: markdown.markdown(general_desc)
    #             html_content += f"<h2>上位类说明</h2><div>{general_desc.replace('\n', '<br>')}</div>"
            
    #         if detail_desc:
    #             html_content += f"<h2>详细沿革</h2><div>{detail_desc.replace('\n', '<br>')}</div>"
            
    #         self.text_display_widget.setHtml(html_content)
    #         self.status_bar.showMessage(f"已显示: {name_display}")
    #     else:
    #         self.text_display_widget.setHtml("<p>未选择区域或无数据。</p>")
    #         self.map_display_widget.display_geometry(None) # Clear map or show default
    #         self.status_bar.showMessage("请选择一个区域。")


if __name__ == '__main__':
    # ... (main_data_processing() call remains the same)
    print(f"Script directory: {SCRIPT_DIR}")
    print(f"Markdown file path: {MD_FILE_PATH}")
    print(f"Maps base directory: {MAPS_BASE_DIR}")

    final_data = main_data_processing() 

    country_geodataframe_for_gui = None # Initialize
    if final_data is not None: 
        temp_shp_data = load_shapefiles() 
        if "country" in temp_shp_data and \
           temp_shp_data["country"] is not None and \
           not temp_shp_data["country"].empty:
            country_geodataframe_for_gui = temp_shp_data["country"] # Pass the whole GeoDataFrame
            print("Country GeoDataFrame loaded for default view.")
        else:
            print("Warning: Country shapefile not found or empty, default map will be placeholder.")

        app = QApplication(sys.argv) # sys.argv is important for QApplication
        window = MainWindow(final_data, country_geodataframe_for_gui)
        window.show()
        sys.exit(app.exec()) # Use sys.exit for proper termination
    else:
        print("\nData processing failed or returned no data. GUI cannot be launched.")