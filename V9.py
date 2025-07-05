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
    QSplitter, QLabel, QDockWidget
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
ProcessedData = List[AdministrativeRegion] # List of provinces


# --- 数据处理函数 (parse_markdown, load_shapefiles, normalize_name, link_data, main_data_processing) ---
# (这里的代码与您V2.py中的版本保持一致，或者使用我们最后确认的版本)
# 为了简洁，我在这里省略这些函数的具体实现，假设它们在您的V2.py中是可用的
# 确保 link_data 函数在末尾返回 md_data

def parse_markdown(md_filepath: str) -> ProcessedData:
    processed_data: ProcessedData = []
    
    current_province: Optional[AdministrativeRegion] = None
    current_city: Optional[AdministrativeRegion] = None
    current_district: Optional[AdministrativeRegion] = None # To hold the current district being processed

    # active_entity points to the entity whose text is currently being collected
    active_entity: Optional[AdministrativeRegion] = None
    # active_field tells which field of the active_entity to append text to
    active_field: str = "text_detail" 

    current_text_buffer: List[str] = []

    def flush_buffer():
        nonlocal active_entity, active_field # Allow modification
        if active_entity and current_text_buffer:
            text_to_add = "\n".join(current_text_buffer).strip()
            if text_to_add: # Only add if there's actual text
                # Initialize field if it doesn't exist or is None
                if active_field not in active_entity or active_entity[active_field] is None:
                    active_entity[active_field] = ""
                
                # Append new text, adding a newline if field already has content
                if active_entity[active_field]: # If there's existing text
                    active_entity[active_field] += "\n" + text_to_add
                else: # If field was empty or just initialized
                    active_entity[active_field] = text_to_add
            current_text_buffer.clear()

    try:
        with open(md_filepath, 'r', encoding='utf-8') as f:
            for line_content in f:
                line = line_content.strip()
                if not line: continue # Skip truly empty lines

                # --- Try matching H1 (Province) ---
                match_h1 = H1_MD_PATTERN.match(line)
                if match_h1:
                    flush_buffer() # Flush text for any previous entity
                    province_name = match_h1.group(1).strip()
                    current_province = {
                        "name": province_name, "level": 1, "adcode": None,
                        "text_general": "", "text_detail": "", # Initialize text fields
                        "geometry": None, "children": []
                    }
                    processed_data.append(current_province)
                    active_entity = current_province
                    active_field = "text_detail" # Text immediately after H1 (before "零、") is part of its detail
                    current_city = None
                    current_district = None
                    continue

                # --- Try matching H2 Special (Province General Description) ---
                if current_province and H2_SPECIAL_ZERO_PATTERN.match(line):
                    flush_buffer() # Flush previous text (should be province's text_detail)
                    active_entity = current_province
                    active_field = "text_general" # Now collecting for province's general text
                    continue

                # --- Try matching H2 (City) ---
                match_h2 = H2_MD_PATTERN.match(line)
                if current_province and match_h2:
                    flush_buffer() # Flush previous text (could be prov_general or prov_detail)
                    city_name = match_h2.group(1).strip()
                    current_city = {
                        "name": city_name, "level": 2, 
                        "parent_name": current_province["name"], "parent_adcode": current_province.get("adcode"),
                        "adcode": None, "text_general": "", "text_detail": "", # Initialize
                        "geometry": None, "children": []
                    }
                    current_province["children"].append(current_city)
                    active_entity = current_city
                    active_field = "text_detail" # Text immediately after H2 (before "0.") is city's detail
                    current_district = None
                    continue
                
                # --- Try matching H3 Special (City General Description) ---
                if current_city and H3_SPECIAL_ZERO_PATTERN.match(line):
                    flush_buffer() # Flush previous text (should be city's text_detail)
                    active_entity = current_city
                    active_field = "text_general" # Now collecting for city's general text
                    continue

                # --- Try matching H3 (District/County) ---
                match_h3 = H3_MD_PATTERN.match(line)
                if current_city and match_h3:
                    flush_buffer() # Flush previous text (could be city_general or city_detail)
                    h3_num_str = match_h3.group(1) # We might not need num_str in the final data if not used
                    h3_name = match_h3.group(2).strip()
                    current_district = {
                        "name": h3_name, "level": 3,
                        "parent_name": current_city["name"], "parent_adcode": current_city.get("adcode"),
                        "adcode": None, "text_general": "", # Districts usually don't have 'text_general' from "0." type titles
                        "text_detail": "", # Initialize
                        "geometry": None
                        # Districts don't have 'children' in this model
                    }
                    # Ensure current_city['children'] was initialized if this is the first district
                    if "children" not in current_city: current_city["children"] = [] 
                    current_city["children"].append(current_district)
                    active_entity = current_district
                    active_field = "text_detail" # Now collecting for district's detail
                    continue
                
                # If none of the above title matches, it's content text for the active_entity and active_field
                current_text_buffer.append(line_content.strip('\n')) # Keep internal newlines, strip trailing only

            # After the loop, flush any remaining text in the buffer
            flush_buffer()

    except FileNotFoundError:
        print(f"Error: Markdown file '{md_filepath}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred while parsing Markdown: {e}")
        import traceback
        traceback.print_exc()
        return []
        
    print(f"Markdown parsing complete. Found {len(processed_data)} provinces.")
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

# --- Color Configuration for Maps ---
LEVEL_COLORS = {
    0: 'lightgrey',  # 国家 (我们用 level 0 代表国家)
    1: '#FF7F7F',    # 省 (淡红色)
    2: '#FFFFBF',    # 市 (淡黄色)
    3: '#7FBFFF',    # 县 (淡蓝色)
    'default': 'lightgrey', # 默认或未知级别
    'edge': 'black' # 统一的边界颜色
}

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

    def display_geometry(self, geometry_to_plot: Optional[Any],
                         fill_color: str = LEVEL_COLORS['default'], 
                         edge_color: str = LEVEL_COLORS['edge'], 
                         fit_bounds: bool = True): # Added color parameters
        """Clears current plot and displays new geometry data with specified color."""
        self.ax.clear()

        can_plot = False
        # ... (can_plot logic from previous version remains the same) ...
        if geometry_to_plot is not None:
            if hasattr(geometry_to_plot, 'empty'): 
                if not geometry_to_plot.empty:
                    can_plot = True
            elif hasattr(geometry_to_plot, 'is_empty'): 
                if not geometry_to_plot.is_empty:
                    can_plot = True
            else: 
                can_plot = True


        if can_plot:
            try:
                if isinstance(geometry_to_plot, (gpd.GeoDataFrame, gpd.GeoSeries)):
                    plotted_geom = geometry_to_plot
                else:
                    plotted_geom = gpd.GeoSeries([geometry_to_plot])
                    # plotted_geom.crs = "EPSG:4326" # Optional: if CRS is known and needed

                # Use the passed fill_color and edge_color
                plotted_geom.plot(ax=self.ax, edgecolor=edge_color, color=fill_color)

                if fit_bounds:
                    # ... (fit_bounds logic from previous version remains the same) ...
                    minx, miny, maxx, maxy = plotted_geom.total_bounds
                    padding_x = (maxx - minx) * 0.1 if (maxx - minx) > 0 else 0.1
                    padding_y = (maxy - miny) * 0.1 if (maxy - miny) > 0 else 0.1
                    self.ax.set_xlim(minx - padding_x - (0.1 if padding_x == 0 else 0), 
                                     maxx + padding_x + (0.1 if padding_x == 0 else 0))
                    self.ax.set_ylim(miny - padding_y - (0.1 if padding_y == 0 else 0), 
                                     maxy + padding_y + (0.1 if padding_y == 0 else 0))

                self.ax.set_aspect('equal', adjustable='box')
            except Exception as e:
                print(f"Error plotting geometry: {e}")
                import traceback
                traceback.print_exc()
                self.ax.text(0.5, 0.5, "无法绘制地图数据", ha='center', va='center')
        else:
            self.ax.text(0.5, 0.5, "无有效地理数据可显示", ha='center', va='center')
        
        # Redraw basic plot styling
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        
        self.canvas.draw()

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

        if self.toggle_browse_action.isChecked():
            self.browse_dock_widget.show()
        else:
            self.browse_dock_widget.hide()

    def init_ui(self):
    
        # --- Menu Bar ---
        menubar = self.menuBar()
        browse_menu = menubar.addMenu("浏览")
        self.toggle_browse_action = QAction("行政区划浏览", self)
        self.toggle_browse_action.setCheckable(True)
        self.toggle_browse_action.setChecked(False)
        self.toggle_browse_action.triggered.connect(self.toggle_browse_panel)
        browse_menu.addAction(self.toggle_browse_action)
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
        
        # Splitter for search/browse and map (within left pane)
        # left_splitter = QSplitter(Qt.Orientation.Vertical)
        # left_splitter.addWidget(self.browse_tree) # Add browse tree here

        self.map_display_widget = MapViewer()
        left_layout.addWidget(self.map_display_widget, stretch=1)
    
        splitter_main.addWidget(left_pane_widget)

        # --- Right Pane (Text Display) ---
        self.text_display_widget = QTextBrowser()
        self.text_display_widget.setOpenExternalLinks(True)
        self.text_display_widget.setMinimumWidth(400)
        splitter_main.addWidget(self.text_display_widget)

        splitter_main.setSizes([450, 800]) # Initial size for left and right panes
        main_layout.addWidget(splitter_main)

        # --- Browse Tree in a Dock Widget (新增/调整位置) ---
        self.browse_dock_widget = QDockWidget("行政区划浏览", self) # 创建DockWidget
        self.browse_tree = QTreeView(self.browse_dock_widget) # 创建TreeView作为DockWidget的内容
        self.browse_tree.setHeaderHidden(True)
        self.tree_model = QStandardItemModel() # 创建数据模型
        self.browse_tree.setModel(self.tree_model) # 为TreeView设置模型
        self.browse_tree.clicked[QModelIndex].connect(self.on_browse_item_selected)
        self.browse_dock_widget.setWidget(self.browse_tree) # 将TreeView放入DockWidget
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.browse_dock_widget) # 将DockWidget添加到主窗口左侧
        self.browse_dock_widget.setVisible(False) # <--- 初始设置为隐藏

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪。")

    def load_default_view(self):
        """Loads the default country map and blank/welcome text."""
        if self.country_geodataframe is not None and not self.country_geodataframe.empty:
            country_color = LEVEL_COLORS.get(0, LEVEL_COLORS['default']) # Get country color (level 0)
            self.map_display_widget.display_geometry(
                self.country_geodataframe,
                fill_color=country_color
            )
            print("Default view: Displaying country map.")
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
        print(f"\nDEBUG: --- Inside update_display_for_region ---") # <--- 调试行1
        print(f"DEBUG:   Received region_data type: {type(region_data)}") # <--- 调试行2
        if isinstance(region_data, dict):
            print(f"DEBUG:   region_data content (sample): {{name: {region_data.get('name')}, level: {region_data.get('level')}}}") # <--- 调试行3
        else:
            print(f"DEBUG:   region_data value: {region_data}") # <--- 调试行4

        if region_data and isinstance(region_data, dict):
            print("DEBUG:   Condition (region_data and isinstance(region_data, dict)) is TRUE.") # <--- 调试行5
            # ... (您的正常处理逻辑)
        else:
            print("DEBUG:   Condition (region_data and isinstance(region_data, dict)) is FALSE. Displaying default.") # <--- 调试行6
            # ... (您的默认视图逻辑)


    def update_display_for_region(self, region_data: Optional[AdministrativeRegion]):
        if region_data and isinstance(region_data, dict):
            current_geometry = region_data.get("geometry")
            current_level = region_data.get("level")
            
            # Determine fill color based on level
            fill_color = LEVEL_COLORS.get(current_level, LEVEL_COLORS['default'])
            
            self.map_display_widget.display_geometry(
                current_geometry,
                fill_color=fill_color
            )

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
            
            # ... (rest of the text display logic remains the same) ...
            name_display = region_data.get('name', '未知区域')
            adcode = region_data.get("adcode", "N/A")
            level_map = {1: "一级政区", 2: "二级政区", 3: "三级政区"}
            level_text = level_map.get(current_level, "未知级别")
            
            html_content = f"<h1>{name_display} <small>({level_text})</small></h1>"
            html_content += f"<p><b>行政代码:</b> {adcode}</p>"

            text_general = region_data.get("text_general", "")
            text_detail = region_data.get("text_detail", "")  
            
            if text_general: # Text from "零./0. 上位类说明"
                html_content += f"<h2>概况</h2><div>{format_text_block(text_general)}</div>"

            if text_detail: # Main body of text
                # Check if text_detail already contains H3 titles from parsing (current simple parser does this)
                # If so, we might want to render them as H3 in HTML too.
                # For now, just format as block.
                html_content += f"<h2>沿革</h2><div>{format_text_block(text_detail)}</div>"
            
            self.text_display_widget.setHtml(html_content)
            self.status_bar.showMessage(f"已显示: {name_display} (代码: {adcode})")
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
            
    def toggle_browse_panel(self):
        if self.browse_dock_widget.isVisible():
            self.browse_dock_widget.hide()
            # self.toggle_browse_action.setChecked(False) # QAction的checkable状态会自动更新
        else:
            self.browse_dock_widget.show()
            # self.toggle_browse_action.setChecked(True)

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