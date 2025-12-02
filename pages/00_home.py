%pip install duckdb leafmap pandas

import duckdb
import pandas as pd
import leafmap.maplibregl as leafmap

con = duckdb.connect()

# 安裝和載入 httpfs (用於遠端檔案存取，如 S3)
con.install_extension("httpfs")
con.load_extension("httpfs")

# 安裝和載入 spatial (用於空間資料處理)
con.install_extension("spatial")
con.load_extension("spatial")

m = leafmap.Map(style="dark-matter")
m.add_basemap("Esri.WorldImagery")
m.add_data(
     gdf,
     layer_type="circle",
     fill_color="#FFD700",
     radius=6,
     stroke_color="#FFFFFF",
     name="NYC Subway Stations"
 )
 m  