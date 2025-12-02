import solara
import duckdb
import pandas as pd
import plotly.express as px
import leafmap.maplibregl as leafmap

# -----------------
# 0. 設定與資料來源
# -----------------
# 實際專案中，這裡可以是您的本地資料庫檔案路徑，例如 'my_spatial_db.duckdb'
# 為了演示，我們繼續使用遠端 CSV，但透過 DuckDB 把它當作資料庫來查詢
DB_SOURCE = 'https://data.gishub.org/duckdb/cities.csv'

# -----------------
# 1. 狀態管理 (Reactive Variables)
# -----------------
all_countries = solara.reactive([])
selected_country = solara.reactive("")

# 新增：人口篩選範圍 (最小值, 最大值)
population_range = solara.reactive((0, 1000000)) 
# 新增：該國家的最大人口數 (用來動態設定 Slider 的上限)
max_population_in_country = solara.reactive(1000000)

data_df = solara.reactive(pd.DataFrame())
is_loading = solara.reactive(False)

# ----------------------------------------------------
# 2. 數據獲取邏輯 (資料庫查詢層)
# ----------------------------------------------------

def get_db_connection():
    """建立 DuckDB 連線並安裝必要擴充"""
    con = duckdb.connect(database=":memory:") # 使用記憶體模式，若有實體檔請改路徑
    con.install_extension("httpfs")
    con.load_extension("httpfs")
    return con

def load_country_list():
    """初始化：載入所有國家清單"""
    print("Loading country list...")
    try:
        con = get_db_connection()
        # 查詢所有國家
        result = con.sql(f"SELECT DISTINCT country FROM '{DB_SOURCE}' ORDER BY country").fetchall()
        country_list = [row[0] for row in result]
        all_countries.set(country_list)
        
        # 預設選取
        if "USA" in country_list:
            selected_country.set("USA")
        elif country_list:
            selected_country.set(country_list[0])
        con.close()
    except Exception as e:
        print(f"Error loading countries: {e}")

def update_country_stats():
    """當切換國家時，先查詢該國家的『最大人口數』，以調整 Slider 的範圍"""
    country = selected_country.value
    if not country: return

    con = get_db_connection()
    try:
        # 找出該國最大城市人口，用來設定 Slider 的上限
        max_pop = con.sql(f"""
            SELECT MAX(population) 
            FROM '{DB_SOURCE}' 
            WHERE country = '{country}'
        """).fetchone()[0]
        
        if max_pop:
            max_population_in_country.set(int(max_pop))
            # 重置篩選範圍：從 0 到 最大值
            population_range.set((0, int(max_pop)))
    except Exception as e:
        print(f"Error getting stats: {e}")
    finally:
        con.close()

def load_filtered_data():
    """主查詢：根據『國家』與『人口滑桿』篩選資料"""
    country = selected_country.value
    pop_min, pop_max = population_range.value
    
    if not country: return
    
    is_loading.set(True)
    print(f"Querying: {country}, Pop: {pop_min}-{pop_max}")
    
    con = get_db_connection()
    try:
        # === 關鍵：這裡模擬將大量圖資轉為資料庫後的 SQL 查詢 ===
        # 我們只撈取符合條件的資料，而不是全部撈出來再用 Python 篩選
        sql_query = f"""
            SELECT name, country, population, latitude, longitude
            FROM '{DB_SOURCE}'
            WHERE country = '{country}'
              AND population BETWEEN {pop_min} AND {pop_max}
            ORDER BY population DESC
            LIMIT 500;  -- 限制回傳筆數，避免瀏覽器崩潰
        """
        df_result = con.sql(sql_query).df()
        data_df.set(df_result)
    except Exception as e:
        print(f"Error executing query: {e}")
        data_df.set(pd.DataFrame())
    finally:
        con.close()
        is_loading.set(False)

# ----------------------------------------------------
# 3. 視覺化組件 (Map & Charts)
# ----------------------------------------------------

@solara.component
def CityMap(df: pd.DataFrame):
    """地圖元件"""
    # 這裡使用 key 來強制 Solara 在資料變更時重新建立地圖元件
    # 這是解決 Leafmap 在 Solara 中更新不流暢的常見技巧
    
    if df.empty:
        return solara.Info("此篩選條件下無資料。")

    # 計算地圖中心點
    center = [df['latitude'].mean(), df['longitude'].mean()]
    
    # 建立地圖
    m = leafmap.Map(
        center=center,
        zoom=5,
        style="carto-positron", # 使用簡潔的底圖
        height="600px"
    )

    # 準備 GeoJSON 資料
    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["longitude"], row["latitude"]]
            },
            "properties": {
                "name": row["name"],
                "population": row["population"],
                # 根據人口大小設定顏色 (這裡簡單示範)
                "color": "#FF5733" if row["population"] > 500000 else "#33FF57"
            }
        })

    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }

    # 加入資料層
    m.add_geojson(
        geojson_data,
        layer_id="cities",
        # 使用圓點繪製
        paint={
            "circle-radius": 6,
            "circle-color": ["get", "color"], # 從 properties 讀取顏色
            "circle-stroke-width": 1,
            "circle-stroke-color": "#ffffff"
        }
    )
    
    return m.to_solara()

# ----------------------------------------------------
# 4. 主頁面佈局
# ----------------------------------------------------
@solara.component
def Page():
    solara.Title("空間資料庫過濾系統")

    # === Effect Hooks (生命週期管理) ===
    # 1. 啟動時載入國家清單
    solara.use_effect(load_country_list, dependencies=[])
    
    # 2. 當國家改變時，更新該國統計數據 (設定 Slider 上限)
    solara.use_effect(update_country_stats, dependencies=[selected_country.value])
    
    # 3. 當 (國家 或 人口範圍) 改變時，重新撈取地圖資料
    solara.use_effect(load_filtered_data, dependencies=[selected_country.value, population_range.value])

    # === 側邊欄：控制面板 ===
    with solara.Sidebar():
        solara.Markdown("## 🛠️ 資料篩選條件")
        solara.Markdown("---")
        
        # 1. 選單
        solara.Select(
            label="選擇國家 (Region)",
            value=selected_country,
            values=all_countries.value
        )
        
        solara.Markdown("<br>")
        
        # 2. 滑動尺標 (Range Slider)
        solara.Markdown(f"**人口數範圍篩選**")
        solara.Markdown(f"目前顯示: {population_range.value[0]:,} - {population_range.value[1]:,} 人")
        
        # 注意：max 值是動態根據該國數據設定的
        solara.SliderRangeInt(
            label="人口區間",
            min=0,
            max=max_population_in_country.value, 
            step=1000,
            value=population_range
        )
        
        solara.Markdown("---")
        solara.Info("調整滑桿後，地圖與圖表將自動透過 SQL 重新查詢。")

    # === 主畫面 ===
    with solara.Column(style={"padding": "20px"}):
        solara.Markdown(f"# 🗺️ {selected_country.value} 空間資料展示")
        
        if is_loading.value:
            solara.ProgressLinear(indeterminate=True)
        else:
            df = data_df.value
            
            # 分頁籤設計
            with solara.LabTabs():
                
                # Tab 1: 地圖
                with solara.LabTab("📍 地圖檢視"):
                    with solara.Card():
                        CityMap(df)
                        solara.Text(f"顯示筆數: {len(df)} 筆 (已過濾)")

                # Tab 2: 統計圖表
                with solara.LabTab("📊 統計分析"):
                    if not df.empty:
                        fig = px.scatter(
                            df, x="population", y="latitude", 
                            size="population", hover_name="name",
                            title="人口 vs 緯度分佈"
                        )
                        solara.FigurePlotly(fig)
                        
                # Tab 3: 資料明細
                with solara.LabTab("📋 資料明細"):
                    solara.DataFrame(df)