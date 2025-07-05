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
    QSplitter, QLabel, QDockWidget, QPushButton # Added missing imports
)
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction

# Matplotlib imports for embedding in PySide6
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    CARTOPY_AVAILABLE = True
except ImportError:
    CARTOPY_AVAILABLE = False
    print("Cartopy not available - world map features will be limited")

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
H3_MD_PATTERN = re.compile(r"^###\s*([1-9]|1[0-9]|2[0-5])\.\s*(.+)$")

AdministrativeRegion = Dict[str, Any]
ProcessedData = List[AdministrativeRegion]

# --- 数据处理函数 (保持原有实现) ---
def parse_markdown(md_filepath: str) -> ProcessedData:
    processed_data: ProcessedData = []
    
    current_province: Optional[AdministrativeRegion] = None
    current_city: Optional[AdministrativeRegion] = None
    current_district: Optional[AdministrativeRegion] = None

    active_entity: Optional[AdministrativeRegion] = None
    active_field: str = "text_detail" 

    current_text_buffer: List[str] = []

    def flush_buffer():
        nonlocal active_entity, active_field
        if active_entity and current_text_buffer:
            text_to_add = "\n".join(current_text_buffer).strip()
            if text_to_add:
                if active_field not in active_entity or active_entity[active_field] is None:
                    active_entity[active_field] = ""
                
                if active_entity[active_field]:
                    active_entity[active_field] += "\n" + text_to_add
                else:
                    active_entity[active_field] = text_to_add
            current_text_buffer.clear()

    try:
        with open(md_filepath, 'r', encoding='utf-8') as f:
            for line_content in f:
                line = line_content.strip()
                if not line: continue

                match_h1 = H1_MD_PATTERN.match(line)
                if match_h1:
                    flush_buffer()
                    province_name = match_h1.group(1).strip()
                    current_province = {
                        "name": province_name, "level": 1, "adcode": None,
                        "text_general": "", "text_detail": "",
                        "geometry": None, "children": []
                    }
                    processed_data.append(current_province)
                    active_entity = current_province
                    active_field = "text_detail"
                    current_city = None
                    current_district = None
                    continue

                if current_province and H2_SPECIAL_ZERO_PATTERN.match(line):
                    flush_buffer()
                    active_entity = current_province
                    active_field = "text_general"
                    continue

                match_h2 = H2_MD_PATTERN.match(line)
                if current_province and match_h2:
                    flush_buffer()
                    city_name = match_h2.group(1).strip()
                    current_city = {
                        "name": city_name, "level": 2, 
                        "parent_name": current_province["name"], "parent_adcode": current_province.get("adcode"),
                        "adcode": None, "text_general": "", "text_detail": "",
                        "geometry": None, "children": []
                    }
                    current_province["children"].append(current_city)
                    active_entity = current_city
                    active_field = "text_detail"
                    current_district = None
                    continue
                
                if current_city and H3_SPECIAL_ZERO_PATTERN.match(line):
                    flush_buffer()
                    active_entity = current_city
                    active_field = "text_general"
                    continue

                match_h3 = H3_MD_PATTERN.match(line)
                if current_city and match_h3:
                    flush_buffer()
                    h3_name = match_h3.group(2).strip()
                    current_district = {
                        "name": h3_name, "level": 3,
                        "parent_name": current_city["name"], "parent_adcode": current_city.get("adcode"),
                        "adcode": None, "text_general": "",
                        "text_detail": "", "geometry": None
                    }
                    if "children" not in current_city: current_city["children"] = [] 
                    current_city["children"].append(current_district)
                    active_entity = current_district
                    active_field = "text_detail"
                    continue
                
                current_text_buffer.append(line_content.strip('\n'))

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
    if name is None: return ""
    name = name.strip()
    suffixes_to_remove = ["省", "市", "区", "县", "自治州", "自治县", "地区", "盟"] 
    for suffix in suffixes_to_remove:
        if name.endswith(suffix) and len(name) > len(suffix): 
            name = name[:-len(suffix)]
    return name

def link_data(md_data: ProcessedData, shp_data: Dict[str, gpd.GeoDataFrame]) -> ProcessedData:
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
    
    gdf_provinces = shp_data["province"]
    gdf_cities = shp_data["city"]
    gdf_districts = shp_data["district"]

    for province_md in md_data:
        prov_name_md_original = province_md["name"]
        prov_name_md_normalized = normalize_name(prov_name_md_original)
        
        if 'pr_name' not in gdf_provinces.columns: continue
        match_condition_series_prov = gdf_provinces['pr_name'].astype(str).apply(normalize_name) == prov_name_md_normalized
        matched_prov_shp = gdf_provinces[match_condition_series_prov]

        if not matched_prov_shp.empty:
            province_shp_row = matched_prov_shp.iloc[0]
            province_md["adcode"] = province_shp_row["pr_adcode"]
            province_md["geometry"] = province_shp_row.geometry

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
                    
                    for district_md in city_md.get("children", []):
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
    
    print("--- Data linking loop finished. ---")
    return md_data

def main_data_processing():
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
    if missing_keys:
        print(f"Shapefile loading incomplete or essential shapefiles are empty. Missing/Empty keys: {missing_keys}. Exiting.")
        return None
    print("--- Calling link_data ---")
    linked_data_structure = link_data(parsed_md, shapefile_data)
    print("--- Returned from link_data ---")
    return linked_data_structure

# --- Color Configuration for Maps ---
LEVEL_COLORS = {
    0: 'lightgrey',  # 国家
    1: '#FF7F7F',    # 省
    2: '#FFFFBF',    # 市
    3: '#7FBFFF',    # 县
    'default': 'lightgrey',
    'edge': 'black'
}

# --- GUI Application Class ---
class MapViewer(QWidget):
    """Widget to display maps with main map and optional mini-map."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        
        # 创建主地图axes (占据大部分空间)
        self.ax_main = self.figure.add_subplot(111)
        # 创建小地图axes (左上角)
        self.ax_mini = self.figure.add_axes([0.02, 0.7, 0.25, 0.25])  # [left, bottom, width, height]
        
        self._setup_axes_style(self.ax_main)
        self._setup_axes_style(self.ax_mini)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.setMinimumSize(500, 400)
        
        # 存储当前显示的数据，用于小地图
        self.current_region = None
        self.all_shapefiles = None

    def _setup_axes_style(self, ax):
        """设置axes的基本样式"""
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    def set_shapefiles_reference(self, shapefiles_dict: Dict[str, gpd.GeoDataFrame]):
        """设置shapefile数据引用，用于小地图显示"""
        self.all_shapefiles = shapefiles_dict

    def display_geometry(self, geometry_to_plot: Optional[Any], 
                        region_data: Optional[AdministrativeRegion] = None,
                        fill_color: str = LEVEL_COLORS['default'], 
                        edge_color: str = LEVEL_COLORS['edge'], 
                        fit_bounds: bool = True):
        """显示主地图和小地图"""
        self.current_region = region_data
        
        # 清空两个axes
        self.ax_main.clear()
        self.ax_mini.clear()
        self._setup_axes_style(self.ax_main)
        self._setup_axes_style(self.ax_mini)
        
        # 显示主地图
        self._plot_main_map(geometry_to_plot, fill_color, edge_color, fit_bounds)
        
        # 显示小地图
        self._plot_mini_map()
        
        self.canvas.draw()

    def _plot_main_map(self, geometry_to_plot, fill_color, edge_color, fit_bounds):
        """绘制主地图"""
        can_plot = self._can_plot_geometry(geometry_to_plot)
        
        if can_plot:
            try:
                if isinstance(geometry_to_plot, (gpd.GeoDataFrame, gpd.GeoSeries)):
                    plotted_geom = geometry_to_plot
                else:
                    plotted_geom = gpd.GeoSeries([geometry_to_plot])

                plotted_geom.plot(ax=self.ax_main, edgecolor=edge_color, color=fill_color)

                if fit_bounds:
                    self._fit_bounds(self.ax_main, plotted_geom)

                self.ax_main.set_aspect('equal', adjustable='box')
            except Exception as e:
                print(f"Error plotting main geometry: {e}")
                self.ax_main.text(0.5, 0.5, "无法绘制地图数据", ha='center', va='center')
        else:
            self.ax_main.text(0.5, 0.5, "无有效地理数据可显示", ha='center', va='center')

    def _plot_mini_map(self):
        """绘制小地图 - 显示上级区域和当前区域位置"""
        if not self.current_region or not self.all_shapefiles:
            return
            
        current_level = self.current_region.get("level")
        
        try:
            if current_level == 1:  # 省级 - 小地图显示全国
                self._show_country_with_province()
            elif current_level == 2:  # 市级 - 小地图显示省内
                self._show_province_with_city()
            elif current_level == 3:  # 区县级 - 小地图显示市内
                self._show_city_with_district()
        except Exception as e:
            print(f"Error plotting mini map: {e}")

    def _show_country_with_province(self):
        """小地图：显示全国边界及当前省份位置"""
        if "country" not in self.all_shapefiles or "province" not in self.all_shapefiles:
            return
            
        country_gdf = self.all_shapefiles["country"]
        province_gdf = self.all_shapefiles["province"]
        
        # 显示国家边界
        country_gdf.plot(ax=self.ax_mini, color=LEVEL_COLORS['default'], 
                        edgecolor=LEVEL_COLORS['edge'], alpha=0.7)
        
        # 高亮当前省份
        current_adcode = self.current_region.get("adcode")
        if current_adcode and 'pr_adcode' in province_gdf.columns:
            current_prov = province_gdf[province_gdf['pr_adcode'] == current_adcode]
            if not current_prov.empty:
                current_prov.plot(ax=self.ax_mini, color=LEVEL_COLORS[1], 
                                edgecolor=LEVEL_COLORS['edge'])
        
        self._fit_bounds(self.ax_mini, country_gdf)

    def _show_country_with_province(self):
        """小地图：显示全国边界及当前省份位置"""
        print(f"Mini map (Province Level): Showing country with province '{self.current_region.get('name')}'") # 调试信息
        if "country" not in self.all_shapefiles or "province" not in self.all_shapefiles:
            print("Mini map (Province Level): Missing country or province shapefile.") # 调试信息
            return
            
        country_gdf = self.all_shapefiles["country"]
        province_gdf = self.all_shapefiles["province"]
        
        # 显示国家边界
        country_gdf.plot(ax=self.ax_mini, color=LEVEL_COLORS['default'],
                        edgecolor=LEVEL_COLORS['edge'], alpha=0.7)
        
        # 高亮当前省份
        current_adcode = self.current_region.get("adcode")
        print(f"Mini map (Province Level): Current province adcode: {current_adcode}") # 调试信息
        if current_adcode and 'pr_adcode' in province_gdf.columns:
            current_prov = province_gdf[province_gdf['pr_adcode'] == current_adcode]
            if not current_prov.empty:
                print(f"Mini map (Province Level): Found current province for highlight.") # 调试信息
                current_prov.plot(ax=self.ax_mini, color=LEVEL_COLORS[1],
                                edgecolor=LEVEL_COLORS['edge'])
            else:
                print(f"Mini map (Province Level): Current province not found in shapefile for adcode {current_adcode}.") # 调试信息
        else:
            print("Mini map (Province Level): Province adcode missing or 'pr_adcode' column not in shapefile.") # 调试信息
        
        self._fit_bounds(self.ax_mini, country_gdf)
        print(f"Mini map (Province Level): Fit bounds to country_gdf. Bounds: {country_gdf.total_bounds}") # 调试信息

    def _show_province_with_city(self):
        """小地图：显示省边界及当前市位置"""
        print(f"Mini map (City Level): Showing province with city '{self.current_region.get('name')}'") # 调试信息
        if "city" not in self.all_shapefiles:
            print("Mini map (City Level): Missing city shapefile.") # 调试信息
            return
            
        city_gdf = self.all_shapefiles["city"]
        parent_adcode = self.current_region.get("parent_adcode")
        print(f"Mini map (City Level): Parent province adcode: {parent_adcode}") # 调试信息

    def _can_plot_geometry(self, geometry):
        """检查几何数据是否可以绘制"""
        if geometry is not None:
            if hasattr(geometry, 'empty'): 
                return not geometry.empty
            elif hasattr(geometry, 'is_empty'): 
                return not geometry.is_empty
            else: 
                return True
        return False

    def _fit_bounds(self, ax, gdf):
        """调整axes的显示范围"""
        try:
            minx, miny, maxx, maxy = gdf.total_bounds
            padding_x = (maxx - minx) * 0.1 if (maxx - minx) > 0 else 0.1
            padding_y = (maxy - miny) * 0.1 if (maxy - miny) > 0 else 0.1
            ax.set_xlim(minx - padding_x - (0.1 if padding_x == 0 else 0), 
                       maxx + padding_x + (0.1 if padding_x == 0 else 0))
            ax.set_ylim(miny - padding_y - (0.1 if padding_y == 0 else 0), 
                       maxy + padding_y + (0.1 if padding_y == 0 else 0))
            ax.set_aspect('equal', adjustable='box')
        except Exception as e:
            print(f"Error fitting bounds: {e}")

    def display_world_with_china(self, china_gdf: Optional[gpd.GeoDataFrame]):
        """显示世界地图和中国位置（用于默认视图）"""
        self.ax_main.clear()
        self.ax_mini.clear()
        self._setup_axes_style(self.ax_main)
        self._setup_axes_style(self.ax_mini)
        
        try:
            if CARTOPY_AVAILABLE:
                # 尝试使用cartopy创建世界地图
                # 设置投影
                proj = ccrs.PlateCarree()
                
                # 重新创建带投影的axes
                self.figure.clear()
                self.ax_main = self.figure.add_subplot(111, projection=proj)
                
                # 添加世界地图特征
                self.ax_main.add_feature(cfeature.LAND, color='lightgray', alpha=0.7)
                self.ax_main.add_feature(cfeature.OCEAN, color='lightblue', alpha=0.3)
                self.ax_main.add_feature(cfeature.COASTLINE, linewidth=0.5)
                self.ax_main.add_feature(cfeature.BORDERS, linewidth=0.5)
                
                # 添加中国边界
                if china_gdf is not None and not china_gdf.empty:
                    # 确保CRS兼容
                    if china_gdf.crs != 'EPSG:4326':
                        china_gdf = china_gdf.to_crs('EPSG:4326')
                    
                    china_gdf.plot(ax=self.ax_main, color=LEVEL_COLORS[0], 
                                 edgecolor='red', linewidth=2, transform=proj)
                
                # 设置全球视图
                self.ax_main.set_global()
                self.ax_main.gridlines(draw_labels=True, alpha=0.3)
            else:
                # 如果没有cartopy，使用简单的matplotlib绘图
                print("Cartopy not available, using simple plot")
                if china_gdf is not None and not china_gdf.empty:
                    china_gdf.plot(ax=self.ax_main, color=LEVEL_COLORS[0], 
                                 edgecolor=LEVEL_COLORS['edge'])
                    self._fit_bounds(self.ax_main, china_gdf)
                else:
                    self.ax_main.text(0.5, 0.5, "中国地图数据", ha='center', va='center')
            
        except Exception as e:
            print(f"Error creating world map: {e}")
            # fallback to simple china map
            if china_gdf is not None and not china_gdf.empty:
                china_gdf.plot(ax=self.ax_main, color=LEVEL_COLORS[0], 
                             edgecolor=LEVEL_COLORS['edge'])
                self._fit_bounds(self.ax_main, china_gdf)
        
        # 小地图保持空白或显示简单的中国轮廓
        if china_gdf is not None and not china_gdf.empty:
            china_gdf.plot(ax=self.ax_mini, color=LEVEL_COLORS[0], 
                         edgecolor=LEVEL_COLORS['edge'], alpha=0.5)
            self._fit_bounds(self.ax_mini, china_gdf)
        
        self.canvas.draw()

class SearchResultsWidget(QWidget):
    """搜索结果显示组件"""
    result_selected = Signal(dict)  # 当搜索结果被选中时发出信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.search_results = []
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 结果列表
        self.results_tree = QTreeView()
        self.results_model = QStandardItemModel()
        self.results_model.setHorizontalHeaderLabels(["搜索结果"])
        self.results_tree.setModel(self.results_model)
        self.results_tree.clicked.connect(self.on_result_clicked)
        
        layout.addWidget(QLabel("搜索结果:"))
        layout.addWidget(self.results_tree)
    
    def display_search_results(self, results: List[AdministrativeRegion]):
        """显示搜索结果"""
        self.search_results = results
        self.results_model.clear()
        self.results_model.setHorizontalHeaderLabels(["搜索结果"])
        
        if not results:
            no_result_item = QStandardItem("未找到匹配结果")
            self.results_model.appendRow(no_result_item)
            return
        
        for i, result in enumerate(results):
            result_text = f"{result['name']} ({self._get_level_text(result['level'])})"
            if result.get('parent_name'):
                result_text += f" - {result['parent_name']}"
            
            result_item = QStandardItem(result_text)
            result_item.setData(i, Qt.UserRole)  # 存储结果索引
            self.results_model.appendRow(result_item)
        
        self.results_tree.expandAll()
    
    def _get_level_text(self, level: int) -> str:
        """获取行政级别的文本描述"""
        level_map = {1: "省", 2: "市", 3: "区/县"}
        return level_map.get(level, "未知")
    
    def on_result_clicked(self, index: QModelIndex):
        """处理搜索结果点击事件"""
        item = self.results_model.itemFromIndex(index)
        if item and item.data(Qt.UserRole) is not None:
            result_index = item.data(Qt.UserRole)
            if 0 <= result_index < len(self.search_results):
                selected_result = self.search_results[result_index]
                self.result_selected.emit(selected_result)

class MainWindow(QMainWindow):
    def __init__(self, data_store: Optional[ProcessedData], country_gdf: Optional[gpd.GeoDataFrame]):
        super().__init__()
        self.data_store = data_store if data_store else []
        self.country_geodataframe = country_gdf
        
        # 加载所有shapefile数据供小地图使用
        self.all_shapefiles = load_shapefiles()

        self.setWindowTitle("九域真形图 - 行政区沿革查询系统")
        self.setGeometry(100, 100, 1400, 900)

        self.init_ui()
        self.load_default_view()
        if self.data_store:
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
        left_layout.setContentsMargins(0,0,0,0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入地名搜索 (至少2个汉字)...")
        self.search_input.returnPressed.connect(self.perform_search)
        
        search_button = QPushButton("搜索")
        search_button.clicked.connect(self.perform_search)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        
        left_layout.addLayout(search_layout)

        # 搜索结果区域
        self.search_results_widget = SearchResultsWidget()
        self.search_results_widget.result_selected.connect(self.on_search_result_selected)
        left_layout.addWidget(self.search_results_widget)

        # 详细信息显示区域
        self.text_display = QTextBrowser()
        self.text_display.setMinimumHeight(200)
        left_layout.addWidget(QLabel("详细信息:"))
        left_layout.addWidget(self.text_display)

        splitter_main.addWidget(left_pane_widget)

        # --- Right Pane (Map) ---
        self.map_viewer = MapViewer()
        self.map_viewer.set_shapefiles_reference(self.all_shapefiles)
        splitter_main.addWidget(self.map_viewer)

        # 设置分割器比例
        splitter_main.setSizes([400, 800])
        main_layout.addWidget(splitter_main)

        # --- Browse Dock Widget ---
        self.browse_dock_widget = QDockWidget("行政区划浏览", self)
        self.browse_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        browse_widget = QWidget()
        browse_layout = QVBoxLayout(browse_widget)
        
        self.browse_tree = QTreeView()
        self.browse_model = QStandardItemModel()
        self.browse_model.setHorizontalHeaderLabels(["行政区划"])
        self.browse_tree.setModel(self.browse_model)
        self.browse_tree.clicked.connect(self.on_browse_tree_clicked)
        
        browse_layout.addWidget(self.browse_tree)
        self.browse_dock_widget.setWidget(browse_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.browse_dock_widget)
        self.browse_dock_widget.hide()  # 默认隐藏

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def perform_search(self):
        """执行搜索功能"""
        query = self.search_input.text().strip()
        if len(query) < 2:
            QMessageBox.information(self, "搜索提示", "请输入至少2个汉字进行搜索")
            return
        
        # 搜索逻辑
        results = self.search_regions(query)
        self.search_results_widget.display_search_results(results)
        
        if results:
            self.status_bar.showMessage(f"找到 {len(results)} 个匹配结果")
        else:
            self.status_bar.showMessage("未找到匹配结果")

    def search_regions(self, query: str) -> List[AdministrativeRegion]:
        """在数据中搜索匹配的行政区域"""
        results = []
        
        def search_in_region(region: AdministrativeRegion):
            if query in region['name']:
                results.append(region)
            
            # 递归搜索子区域
            for child in region.get('children', []):
                search_in_region(child)
        
        # 在所有省份中搜索
        for province in self.data_store:
            search_in_region(province)
        
        return results

    def on_search_result_selected(self, region_data: AdministrativeRegion):
        """处理搜索结果选择事件"""
        self.display_region_info(region_data)

    def populate_browse_tree(self):
        """填充浏览树"""
        if not self.data_store:
            return
        
        self.browse_model.clear()
        self.browse_model.setHorizontalHeaderLabels(["行政区划"])
        
        for province in self.data_store:
            province_item = QStandardItem(province['name'])
            province_item.setData(province, Qt.UserRole)
            
            for city in province.get('children', []):
                city_item = QStandardItem(city['name'])
                city_item.setData(city, Qt.UserRole)
                
                for district in city.get('children', []):
                    district_item = QStandardItem(district['name'])
                    district_item.setData(district, Qt.UserRole)
                    city_item.appendRow(district_item)
                
                province_item.appendRow(city_item)
            
            self.browse_model.appendRow(province_item)

    def on_browse_tree_clicked(self, index: QModelIndex):
        """处理浏览树点击事件"""
        item = self.browse_model.itemFromIndex(index)
        if item:
            region_data = item.data(Qt.UserRole)
            if region_data:
                self.display_region_info(region_data)

    def display_region_info(self, region_data: AdministrativeRegion):
        """显示区域信息"""
        # 显示文本信息
        info_html = self.format_region_info(region_data)
        self.text_display.setHtml(info_html)
        
        # 显示地图
        geometry = region_data.get('geometry')
        level = region_data.get('level', 0)
        color = LEVEL_COLORS.get(level, LEVEL_COLORS['default'])
        
        self.map_viewer.display_geometry(geometry, region_data, color, LEVEL_COLORS['edge'])
        
        # 更新状态栏
        level_text = {1: "省", 2: "市", 3: "区/县"}.get(level, "区域")
        self.status_bar.showMessage(f"正在显示: {region_data['name']} ({level_text})")

    def format_region_info(self, region_data: AdministrativeRegion) -> str:
        """格式化区域信息为HTML"""
        name = region_data.get('name', '未知')
        level = region_data.get('level', 0)
        adcode = region_data.get('adcode', '无')
        parent_name = region_data.get('parent_name', '')
        
        level_text = {1: "省级", 2: "市级", 3: "区/县级"}.get(level, "未知级别")
        
        html = f"""
        <h2>{name}</h2>
        <p><strong>行政级别:</strong> {level_text}</p>
        <p><strong>行政代码:</strong> {adcode}</p>
        """
        
        if parent_name:
            html += f"<p><strong>上级区域:</strong> {parent_name}</p>"
        
        # 添加概述信息
        text_general = region_data.get('text_general', '').strip()
        if text_general:
            html += f"<h3>概述</h3><p>{text_general.replace(chr(10), '<br>')}</p>"
        
        # 添加详细信息
        text_detail = region_data.get('text_detail', '').strip()
        if text_detail:
            html += f"<h3>详细信息</h3><p>{text_detail.replace(chr(10), '<br>')}</p>"
        
        # 添加子区域信息
        children = region_data.get('children', [])
        if children:
            child_level_text = {1: "下辖市", 2: "下辖区/县"}.get(level, "下级区域")
            html += f"<h3>{child_level_text} ({len(children)}个)</h3><ul>"
            for child in children:
                html += f"<li>{child['name']}</li>"
            html += "</ul>"
        
        return html

    def load_default_view(self):
        """加载默认视图"""
        if self.country_geodataframe is not None and not self.country_geodataframe.empty:
            self.map_viewer.display_world_with_china(self.country_geodataframe)
            self.text_display.setHtml("""
                <h2>九域真形图 - 行政区沿革查询系统</h2>
                <p>欢迎使用九域真形图系统！</p>
                <p>您可以通过以下方式探索中国行政区划信息：</p>
                <ul>
                    <li><strong>搜索功能:</strong> 在左上角搜索框中输入地名进行搜索</li>
                    <li><strong>浏览功能:</strong> 通过菜单栏打开"行政区划浏览"面板</li>
                </ul>
                <p>系统将显示相应的地理位置、行政信息和历史沿革。</p>
            """)
            self.status_bar.showMessage("系统已就绪 - 中国地图已加载")
        else:
            self.text_display.setHtml("""
                <h2>九域真形图 - 行政区沿革查询系统</h2>
                <p><strong>注意:</strong> 地图数据未找到</p>
                <p>请确保以下文件存在：</p>
                <ul>
                    <li>maps/1.Country/country.shp</li>
                    <li>maps/2.Province/province.shp</li>
                    <li>maps/3.City/city.shp</li>
                    <li>maps/4.District/district.shp</li>
                    <li>output.md</li>
                </ul>
            """)
            self.status_bar.showMessage("警告: 地图数据未加载")

    def toggle_browse_panel(self):
        """切换浏览面板的显示/隐藏"""
        if self.toggle_browse_action.isChecked():
            self.browse_dock_widget.show()
        else:
            self.browse_dock_widget.hide()

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = """
        <h2>九域真形图 - 行政区沿革查询系统</h2>
        <p><strong>版本:</strong> 1.0.0</p>
        <p><strong>描述:</strong> 基于历史文献的中国行政区划查询与可视化系统</p>
        <br>
        <p><strong>主要功能:</strong></p>
        <ul>
            <li>行政区划地图可视化</li>
            <li>多级行政区划浏览</li>
            <li>地名搜索功能</li>
            <li>历史沿革信息展示</li>
        </ul>
        <br>
        <p><strong>技术栈:</strong></p>
        <ul>
            <li>Python 3.x</li>
            <li>PySide6 (Qt for Python)</li>
            <li>GeoPandas & Matplotlib</li>
            <li>Cartopy (可选)</li>
        </ul>
        """
        
        QMessageBox.about(self, "关于九域真形图", about_text)

# --- Main Application Function ---
def main():
    """主程序入口"""
    app = QApplication(sys.argv)
    app.setApplicationName("九域真形图")
    app.setApplicationVersion("1.0.0")
    
    # 设置应用图标（如果有的话）
    # app.setWindowIcon(QIcon("icon.png"))
    
    print("正在加载数据...")
    
    # 加载和处理数据
    processed_data = main_data_processing()
    
    # 加载国家边界数据
    shapefiles = load_shapefiles()
    country_gdf = shapefiles.get("country")
    
    if processed_data:
        print(f"数据加载成功 - 找到 {len(processed_data)} 个省级行政区")
    else:
        print("警告: 数据加载失败或为空")
    
    # 创建主窗口
    main_window = MainWindow(processed_data, country_gdf)
    main_window.show()
    
    print("应用程序已启动")
    
    # 运行应用
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("程序被用户中断")
        sys.exit(0)

if __name__ == "__main__":
    main()