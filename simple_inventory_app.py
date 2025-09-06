import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# Configure page
st.set_page_config(
    page_title="Inventory Dashboard", 
    layout="wide"
)

# Modern CSS without icons
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        max-width: 1200px;
    }
    .metric-box {
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        text-align: center;
    }
    .metric-number {
        font-size: 24px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 5px;
    }
    .metric-text {
        font-size: 14px;
        color: #6c757d;
    }
    .warehouse-row {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 8px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .warehouse-name {
        font-weight: 600;
        color: #495057;
        font-size: 16px;
    }
    .warehouse-quantity {
        font-size: 18px;
        font-weight: bold;
        color: #28a745;
    }
</style>
""", unsafe_allow_html=True)

# Arabic display names for warehouses
WAREHOUSE_DISPLAY_NAMES = {
    'POS/الصالة': 'الصالة',
    'Virtual Locations/تذوق': 'تذوق',
    'Virtual Locations/عينات': 'عينات',
    'Virtual Locations/مستلزمات المبيعات والتشغيل': 'مستلزمات المبيعات والتشغيل',
    'Virtual Locations/هالك': 'هالك',
    'WH-pr/مخزن الانتاج': 'مخزن الانتاج',
    'WH/المخزن الرئيسى': 'المخزن الرئيسي',
    'cairo/مخزن القاهرة': 'مخزن القاهرة',
    'other/مخزون لدي الغير شيخون': 'مخزون لدي الغير شيخون',
    'sadat/مخزن السادات': 'مخزن السادات',
    'wh-p/مخزون المنتج التام': 'مخزون المنتج التام',
    'zagel/مخزن زاجل': 'مخزن زاجل',
    'تحويل/المخزون': 'تحويل المخزون',
    'ثلاجه/المخزون': 'ثلاجه',
    'حيدوي/المخزون': 'حيدوي',
    'ساحل/المخزون': 'ساحل',
    'شحن/المخزون': 'شحن',
    'صابون/المخزون': 'صابون',
    'فتحي/المخزون': 'فتحي'
}

class InventoryProcessor:
    def __init__(self, df):
        self.raw_df = df.copy()
        
    def process_data(self):
        try:
            df = self.raw_df.copy()
            processed_data = []
            current_date = None
            
            # All warehouse locations
            warehouses = [
                'POS/الصالة',
                'Virtual Locations/تذوق', 
                'Virtual Locations/عينات',
                'Virtual Locations/مستلزمات المبيعات والتشغيل',
                'Virtual Locations/هالك',
                'WH-pr/مخزن الانتاج',
                'WH/المخزن الرئيسى', 
                'cairo/مخزن القاهرة',
                'other/مخزون لدي الغير شيخون',
                'sadat/مخزن السادات',
                'wh-p/مخزون المنتج التام',
                'zagel/مخزن زاجل',
                'تحويل/المخزون',
                'ثلاجه/المخزون', 
                'حيدوي/المخزون',
                'ساحل/المخزون',
                'شحن/المخزون',
                'صابون/المخزون',
                'فتحي/المخزون'
            ]
            
            warehouse_mapping = self._map_warehouses(df.columns, warehouses)
            
            for idx, row in df.iterrows():
                first_col = str(row.iloc[0]).strip()
                
                # Skip headers
                if any(word in first_col for word in ['التعداد', 'الكمية', 'Column']):
                    continue
                
                # Check for date
                if self._is_date(first_col):
                    current_date = first_col
                    continue
                
                # Check for product
                if self._is_product(row, first_col):
                    product_data = self._extract_quantities(row, current_date, warehouse_mapping)
                    if product_data:
                        processed_data.extend(product_data)
            
            if processed_data:
                return pd.DataFrame(processed_data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Error processing data: {e}")
            return pd.DataFrame()
    
    def _map_warehouses(self, columns, warehouses):
        """
        Robust mapping: match warehouse with column name by stripping spaces and checking substring inclusion.
        """
        mapping = {}
        columns_stripped = [str(col).strip() for col in columns]
        for warehouse in warehouses:
            warehouse_stripped = warehouse.strip()
            for i, col in enumerate(columns_stripped):
                col_stripped = col.strip()
                # Match if warehouse name is in column name or vice versa
                if warehouse_stripped in col_stripped or col_stripped in warehouse_stripped:
                    mapping[warehouse_stripped] = i
                    break
        return mapping
    
    def _is_date(self, text):
        """Check if row contains date"""
        if not text or text == 'nan':
            return False
        
        date_patterns = [
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}',
            r'(June|July|August|September|October|November|December)\s+\d{4}',
            r'\d{1,2}\s+[A-Za-z]+\s+\d{4}',     # Generic Month
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',   # DD-MM-YYYY or DD/MM/YYYY
        ]
        
        return any(re.search(p, text, re.IGNORECASE) for p in date_patterns)
    
    def _is_product(self, row, first_col):
        """Check if row contains product"""
        if not first_col or first_col == 'nan':
            return False
        
        has_product_code = re.search(r'\[\d+\]', first_col)
        has_arabic = any('\u0600' <= char <= '\u06FF' for char in first_col)
        has_data = any(self._to_float(val) > 0 for val in row.iloc[1:] if not pd.isna(val))
        
        return has_product_code or (has_arabic and has_data)
    
    def _extract_quantities(self, row, current_date, warehouse_mapping):
        """Extract product quantities from each warehouse"""
        try:
            product_name = str(row.iloc[0]).strip()
            if not product_name or product_name == 'nan':
                return []
            
            data_points = []
            for warehouse_name, quantity_idx in warehouse_mapping.items():
                if quantity_idx < len(row):
                    quantity = self._to_float(row.iloc[quantity_idx])
                    data_points.append({
                        'Product': product_name,
                        'Date': current_date or 'Unknown',
                        'Location': warehouse_name,
                        'Quantity': quantity
                    })
            return data_points
        except Exception as e:
            return []
    
    def _to_float(self, value):
        """Convert value to float - exact number from sheet"""
        try:
            if pd.isna(value):
                return 0.0
            str_val = str(value).replace(',', '').strip()
            return float(str_val) if str_val and str_val != 'nan' else 0.0
        except:
            return 0.0

def format_number(num):
    """Format numbers for display"""
    try:
        return f"{num:,.2f}"
    except:
        return str(num)

def main():
    st.title("Inventory Dashboard")
    st.markdown("**تتبع كميات المنتجات في جميع المخازن (كل المخازن وليس مخزن واحد فقط)**")
    
    uploaded_file = st.file_uploader("ارفع ملف المخزون (CSV)", type=['csv'])
    
    if uploaded_file:
        try:
            with st.spinner("جاري معالجة بيانات المخزون ..."):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
                processor = InventoryProcessor(df)
                data = processor.process_data()
            
            if data.empty:
                st.error("لم يتم العثور على بيانات في الملف")
                return
            
            st.success(f"تم تحميل {len(data)} سجل مخزون")
            
            products = sorted(data['Product'].unique())
            warehouses = sorted(data['Location'].unique())
            dates = sorted(data['Date'].unique())
            
            tab1, tab2, tab3 = st.tabs(["بحث بالمنتج", "بحث بالتاريخ", "رسوم بيانية"])
            
            # --- بحث المنتج مع فلترة المخزن ---
            with tab1:
                st.header("بحث المنتج")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    selected_product = st.selectbox("اختر المنتج:", [""] + products, key="product_search")
                with col2:
                    date_filter = st.selectbox("فلترة بالتاريخ:", ["كل التواريخ"] + dates, key="product_date")
                
                filter_type = st.radio(
                    "نوع الفلترة للمخزن:",
                    ["كل المخازن", "المخازن التي بها كمية (>0)", "اختيار يدوي"],
                    index=0
                )
                
                product_data = pd.DataFrame()
                filtered_warehouses = warehouses
                if selected_product:
                    product_data = data[data['Product'] == selected_product].copy()
                    if date_filter != "كل التواريخ":
                        product_data = product_data[product_data['Date'] == date_filter]
                    warehouses_with_qty = sorted(product_data[product_data['Quantity'] > 0]['Location'].unique())
                    
                    if filter_type == "كل المخازن":
                        filtered_warehouses = warehouses
                    elif filter_type == "المخازن التي بها كمية (>0)":
                        filtered_warehouses = warehouses_with_qty
                    else:
                        filtered_warehouses = st.multiselect(
                            "حدد المخازن:",
                            warehouses,
                            default=warehouses_with_qty if warehouses_with_qty else warehouses,
                            key="warehouse_filter"
                        )
                    
                    product_data = product_data[product_data['Location'].isin(filtered_warehouses)]
                    warehouse_summary = (
                        pd.DataFrame({'Location': filtered_warehouses})
                        .set_index('Location')
                        .join(
                            product_data.groupby('Location')['Quantity'].sum(),
                            how='left'
                        )
                        .fillna(0)
                        .sort_values('Quantity', ascending=False)
                    )
                    
                    if not product_data.empty or len(filtered_warehouses) > 0:
                        st.markdown(f"### {selected_product}")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            total_qty = warehouse_summary['Quantity'].sum()
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{format_number(total_qty)}</div>
                                <div class="metric-text">إجمالي الكمية</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col2:
                            warehouse_count = len(filtered_warehouses)
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{warehouse_count}</div>
                                <div class="metric-text">عدد المخازن</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col3:
                            date_count = len(product_data['Date'].unique())
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{date_count}</div>
                                <div class="metric-text">عدد التواريخ</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col4:
                            avg_qty = warehouse_summary['Quantity'].mean()
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{format_number(avg_qty)}</div>
                                <div class="metric-text">متوسط الكمية</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.subheader("الكميات حسب المخزن")
                        for location, row in warehouse_summary.iterrows():
                            display_name = WAREHOUSE_DISPLAY_NAMES.get(location, location)
                            st.markdown(f"""
                            <div class="warehouse-row">
                                <div class="warehouse-name">{display_name}</div>
                                <div class="warehouse-quantity">{row['Quantity']:,.2f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        st.bar_chart(warehouse_summary['Quantity'])
                        
                        if len(product_data['Date'].unique()) > 1:
                            st.subheader("تسلسل الكميات عبر الزمن")
                            timeline_data = product_data.groupby('Date')['Quantity'].sum().reset_index()
                            st.line_chart(timeline_data.set_index('Date'))
                        
                        st.subheader("البيانات التفصيلية")
                        display_data = product_data[['Date', 'Location', 'Quantity']].copy()
                        st.dataframe(display_data, use_container_width=True)
                    else:
                        st.info("لا توجد بيانات للمنتج أو الفلتر المحدد")
            
            # --- بحث التاريخ مع فلترة المخزن ---
            with tab2:
                st.header("بحث بالتاريخ")
                
                selected_date = st.selectbox("اختر التاريخ:", dates, key="date_search")
                filter_type_date = st.radio(
                    "نوع الفلترة للمخزن:",
                    ["كل المخازن", "المخازن التي بها كمية (>0)", "اختيار يدوي"],
                    index=0,
                    key="warehouse_filter_date_type"
                )
                
                date_data = pd.DataFrame()
                filtered_warehouses_date = warehouses
                if selected_date:
                    date_data = data[data['Date'] == selected_date].copy()
                    warehouses_with_qty_date = sorted(date_data[date_data['Quantity'] > 0]['Location'].unique())
                    
                    if filter_type_date == "كل المخازن":
                        filtered_warehouses_date = warehouses
                    elif filter_type_date == "المخازن التي بها كمية (>0)":
                        filtered_warehouses_date = warehouses_with_qty_date
                    else:
                        filtered_warehouses_date = st.multiselect(
                            "حدد المخازن:",
                            warehouses,
                            default=warehouses_with_qty_date if warehouses_with_qty_date else warehouses,
                            key="warehouse_filter_date"
                        )
                    
                    date_data = date_data[date_data['Location'].isin(filtered_warehouses_date)]
                    warehouse_dist = (
                        pd.DataFrame({'Location': filtered_warehouses_date})
                        .set_index('Location')
                        .join(
                            date_data.groupby('Location')['Quantity'].sum(),
                            how='left'
                        )
                        .fillna(0)
                        .sort_values('Quantity', ascending=False)
                    )
                    
                    if not date_data.empty or len(filtered_warehouses_date) > 0:
                        st.markdown(f"### {selected_date}")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            total_products = len(date_data['Product'].unique())
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{total_products}</div>
                                <div class="metric-text">عدد المنتجات</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col2:
                            total_qty = warehouse_dist['Quantity'].sum()
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{format_number(total_qty)}</div>
                                <div class="metric-text">إجمالي الكمية</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col3:
                            total_warehouses = len(filtered_warehouses_date)
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{total_warehouses}</div>
                                <div class="metric-text">عدد المخازن</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col4:
                            avg_per_product = total_qty / total_products if total_products > 0 else 0
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{format_number(avg_per_product)}</div>
                                <div class="metric-text">متوسط لكل منتج</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.subheader("توزيع الكمية حسب المخزن")
                        for location, row in warehouse_dist.iterrows():
                            display_name = WAREHOUSE_DISPLAY_NAMES.get(location, location)
                            st.markdown(f"""
                            <div class="warehouse-row">
                                <div class="warehouse-name">{display_name}</div>
                                <div class="warehouse-quantity">{row['Quantity']:,.2f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        st.bar_chart(warehouse_dist['Quantity'])
                        
                        st.subheader("أعلى المنتجات حسب الكمية")
                        top_products = date_data.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(10)
                        if not top_products.empty:
                            st.bar_chart(top_products)
                        
                        st.subheader("كل عمليات المخزون")
                        display_data = date_data[['Product', 'Location', 'Quantity']].copy()
                        st.dataframe(display_data, use_container_width=True)
                    else:
                        st.info(f"لا توجد بيانات لهذا التاريخ أو الفلتر المحدد")
            
            # --- رسوم بيانية معبرة اضافية ---
            with tab3:
                st.header("رسوم بيانية معبرة")
                st.markdown("اختر الرسم البياني المناسب لعرض ملخصات المخزون بشكل مرئي:")

                chart_type = st.selectbox("اختر نوع الرسم البياني:", [
                    "أعلى 10 منتجات حسب الكمية الإجمالية",
                    "توزيع الكمية حسب المخزن (Pie)",
                    "تسلسل الكميات عبر الزمن (Line)",
                    "توزيع المنتجات حسب عدد المخازن",
                    "توزيع المنتجات حسب عدد التواريخ",
                    "أكثر المنتجات تواجداً في المخازن",
                    "توزيع الكميات في جميع المخازن (Boxplot)"
                ])
                if st.button("عرض الرسم البياني"):
                    if chart_type == "أعلى 10 منتجات حسب الكمية الإجمالية":
                        top_products = data.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(10)
                        st.bar_chart(top_products)
                    elif chart_type == "توزيع الكمية حسب المخزن (Pie)":
                        warehouse_totals = data.groupby('Location')['Quantity'].sum().sort_values(ascending=False)
                        st.pyplot(pd.DataFrame({'كمية': warehouse_totals}).plot.pie(y='كمية', autopct='%.2f%%', figsize=(6, 6)).figure)
                    elif chart_type == "تسلسل الكميات عبر الزمن (Line)":
                        timeline = data.groupby('Date')['Quantity'].sum().reset_index()
                        st.line_chart(timeline.set_index('Date'))
                    elif chart_type == "توزيع المنتجات حسب عدد المخازن":
                        product_warehouse_count = data.groupby('Product')['Location'].nunique().sort_values(ascending=False)
                        st.bar_chart(product_warehouse_count)
                    elif chart_type == "توزيع المنتجات حسب عدد التواريخ":
                        product_date_count = data.groupby('Product')['Date'].nunique().sort_values(ascending=False)
                        st.bar_chart(product_date_count)
                    elif chart_type == "أكثر المنتجات تواجداً في المخازن":
                        product_qty_per_warehouse = data.groupby(['Product', 'Location'])['Quantity'].sum().reset_index()
                        pivot = product_qty_per_warehouse.pivot(index='Product', columns='Location', values='Quantity').fillna(0)
                        st.dataframe(pivot)
                    elif chart_type == "توزيع الكميات في جميع المخازن (Boxplot)":
                        import matplotlib.pyplot as plt
                        import seaborn as sns
                        fig, ax = plt.subplots(figsize=(10,5))
                        sns.boxplot(x='Location', y='Quantity', data=data)
                        plt.xticks(rotation=45)
                        st.pyplot(fig)
        
        except Exception as e:
            st.error(f"خطأ في معالجة الملف: {str(e)}")
    else:
        st.markdown("""
        """)

if __name__ == "__main__":
    main()
