import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import re
from typing import List, Dict, Optional

# Configure page
st.set_page_config(
    page_title="مخزون فيرجينيا - Virginia Inventory",
    page_icon="📦",
    layout="wide"
)

# Custom CSS for modern design with Arabic support
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin: 0;
    }
    .warehouse-table {
        font-size: 14px;
        margin: 10px 0;
    }
    .warehouse-table th {
        background-color: #f0f2f6;
        padding: 8px;
        text-align: right;
    }
    .warehouse-table td {
        padding: 6px 8px;
        text-align: right;
        border-bottom: 1px solid #e1e5e9;
    }
    .search-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
    }
    .total-row {
        background-color: #e3f2fd;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class InventoryProcessor:
    """Enhanced processor for Virginia inventory data"""
    
    def __init__(self, df):
        self.raw_df = df.copy()
        self.processed_df = None
        self.location_columns = {}
        
    def process_data(self):
        """Process CSV data to extract all warehouse quantities"""
        try:
            df = self.raw_df.copy()
            processed_data = []
            current_date = None
            
            # Map location columns
            self.location_columns = self._map_location_columns(df.columns)
            
            for idx, row in df.iterrows():
                first_col = str(row.iloc[0]).strip()
                
                # Skip header/label rows
                if self._is_header_row(first_col):
                    continue
                
                # Check if this is a date row
                if self._is_date_row(first_col):
                    current_date = self._parse_date(first_col)
                    continue
                
                # Check if this is a product row
                if self._is_product_row(row, first_col):
                    product_data = self._extract_all_warehouse_data(row, current_date)
                    if product_data:
                        processed_data.extend(product_data)
            
            if processed_data:
                self.processed_df = pd.DataFrame(processed_data)
                self._clean_and_sort_data()
                return self.processed_df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"خطأ في معالجة البيانات / Error processing data: {e}")
            return pd.DataFrame()
    
    def _map_location_columns(self, columns):
        """Map all warehouse location columns"""
        location_map = {}
        
        # All warehouse locations from your CSV
        locations = {
            'POS/الصالة': 'الصالة',
            'Virtual Locations/تذوق': 'تذوق',
            'Virtual Locations/عينات': 'عينات',
            'Virtual Locations/مستلزمات المبيعات والتشغيل': 'مستلزمات المبيعات',
            'Virtual Locations/هالك': 'هالك',
            'WH-pr/مخزن الانتاج': 'مخزن الإنتاج',
            'WH/المخزن الرئيسى': 'المخزن الرئيسي',
            'cairo/مخزن القاهرة': 'مخزن القاهرة',
            'other/مخزون لدي الغير شيخون': 'مخزون لدي الغير',
            'sadat/مخزن السادات': 'مخزن السادات',
            'wh-p/مخزون المنتج التام': 'المنتج التام',
            'zagel/مخزن زاجل': 'مخزن زاجل',
            'تحويل/المخزون': 'تحويل المخزون',
            'ثلاجه/المخزون': 'ثلاجة المخزون',
            'حيدوي/المخزون': 'حيدوي المخزون',
            'ساحل/المخزون': 'ساحل المخزون',
            'شحن/المخزون': 'شحن المخزون',
            'صابون/المخزون': 'صابون المخزون',
            'فتحي/المخزون': 'فتحي المخزون'
        }
        
        for i, col in enumerate(columns):
            col_str = str(col)
            for location_key, clean_name in locations.items():
                if location_key in col_str:
                    location_map[clean_name] = i
                    break
        
        return location_map
    
    def _is_header_row(self, text):
        """Check if row is header/label row"""
        if not text or text == 'nan':
            return False
        
        header_indicators = [
            'الكمية بوحدة قياس المنتج',
            'Column0',
            'التعداد',
            'الكمية'
        ]
        
        return any(indicator in text for indicator in header_indicators)
    
    def _is_date_row(self, text):
        """Check if row contains date"""
        if not text or text == 'nan':
            return False
        
        date_patterns = [
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
            r'\d{1,2}\s+(يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+\d{4}'
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
    
    def _parse_date(self, date_string):
        """Parse date string"""
        try:
            # Handle English dates
            date_formats = ['%d %b %Y', '%d %B %Y', '%B %Y', '%b %Y']
            for fmt in date_formats:
                try:
                    parsed = datetime.strptime(date_string.strip(), fmt)
                    return parsed.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            return date_string
        except:
            return date_string
    
    def _is_product_row(self, row, first_col):
        """Check if row contains product data"""
        if not first_col or first_col == 'nan':
            return False
        
        # Look for product code in brackets or Arabic product names
        has_product_code = re.search(r'\[\d+\]', first_col)
        has_arabic = any('\u0600' <= char <= '\u06FF' for char in first_col)
        has_data = any(self._safe_float(val) > 0 for val in row.iloc[1:] if not pd.isna(val))
        
        return (has_product_code or has_arabic) and has_data
    
    def _extract_all_warehouse_data(self, row, current_date):
        """Extract product quantities from all warehouses"""
        try:
            product_name = str(row.iloc[0]).strip()
            if not product_name or product_name == 'nan':
                return []
            
            data_points = []
            
            for warehouse_name, col_index in self.location_columns.items():
                if col_index < len(row):
                    quantity = self._safe_float(row.iloc[col_index])
                    
                    if quantity > 0:  # Only add warehouses with stock
                        data_points.append({
                            'Product': product_name,
                            'Date': current_date or 'غير محدد',
                            'Warehouse': warehouse_name,
                            'Quantity': quantity
                        })
            
            return data_points
            
        except Exception as e:
            return []
    
    def _safe_float(self, value):
        """Convert value to float safely"""
        try:
            if pd.isna(value) or value == '' or str(value).strip() == '':
                return 0.0
            
            # Remove commas and clean the string
            str_val = str(value).replace(',', '').replace('"', '').strip()
            
            if str_val == 'nan' or str_val == '':
                return 0.0
                
            return float(str_val)
        except:
            return 0.0
    
    def _clean_and_sort_data(self):
        """Clean and sort processed data"""
        if self.processed_df is not None and not self.processed_df.empty:
            # Remove rows with no quantity
            self.processed_df = self.processed_df[self.processed_df['Quantity'] > 0]
            
            # Clean product names
            self.processed_df['Product'] = self.processed_df['Product'].str.strip()
            
            # Sort data
            self.processed_df = self.processed_df.sort_values(['Date', 'Product', 'Warehouse'])

def format_number(num):
    """Format numbers for display"""
    try:
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return f"{num:,.2f}"
    except:
        return str(num)

def display_warehouse_table(product_data):
    """Display warehouse quantities in a formatted table"""
    if product_data.empty:
        return
    
    # Group by warehouse and sum quantities
    warehouse_summary = product_data.groupby('Warehouse')['Quantity'].sum().reset_index()
    warehouse_summary = warehouse_summary.sort_values('Quantity', ascending=False)
    
    # Create HTML table
    table_html = '<table class="warehouse-table" style="width: 100%; border-collapse: collapse;">'
    table_html += '<thead><tr><th>المخزن / Warehouse</th><th>الكمية / Quantity</th></tr></thead>'
    table_html += '<tbody>'
    
    total_quantity = 0
    for _, row in warehouse_summary.iterrows():
        quantity = row['Quantity']
        total_quantity += quantity
        table_html += f'<tr><td>{row["Warehouse"]}</td><td style="text-align: left;">{format_number(quantity)}</td></tr>'
    
    # Add total row
    table_html += f'<tr class="total-row"><td><strong>الإجمالي / Total</strong></td><td style="text-align: left;"><strong>{format_number(total_quantity)}</strong></td></tr>'
    table_html += '</tbody></table>'
    
    st.markdown(table_html, unsafe_allow_html=True)

def main():
    st.title("📦 نظام مخزون فيرجينيا / Virginia Inventory System")
    st.markdown("**البحث في المنتجات وتتبع الكميات في جميع المخازن / Search products and track quantities across all warehouses**")
    
    # File upload
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "ارفع ملف المخزون CSV / Upload inventory CSV file", 
        type=['csv'],
        help="ارفع ملف CSV الخاص بالمخزون / Upload your inventory CSV file"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_file is not None:
        try:
            # Process data
            with st.spinner("معالجة بيانات المخزون... / Processing inventory data..."):
                # Try different encodings
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                    except:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, encoding='cp1256')
                
                processor = InventoryProcessor(df)
                data = processor.process_data()
            
            if data.empty:
                st.error("❌ لا يمكن معالجة البيانات من الملف / No data could be processed from the file")
                return
            
            st.success(f"✅ تم معالجة {len(data)} سجل مخزون / Processed {len(data)} inventory records")
            
            # Get unique values for filters
            products = sorted(data['Product'].unique().tolist())
            warehouses = sorted(data['Warehouse'].unique().tolist())
            dates = sorted(data['Date'].unique().tolist())
            
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_products = len(products)
                st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-value">{total_products}</p>
                    <p class="metric-label">إجمالي المنتجات<br>Total Products</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                total_warehouses = len(warehouses)
                st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-value">{total_warehouses}</p>
                    <p class="metric-label">إجمالي المخازن<br>Total Warehouses</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                total_quantity = data['Quantity'].sum()
                st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-value">{format_number(total_quantity)}</p>
                    <p class="metric-label">إجمالي الكمية<br>Total Quantity</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                total_records = len(data)
                st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-value">{total_records}</p>
                    <p class="metric-label">إجمالي السجلات<br>Total Records</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Main functionality tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "🔍 البحث في المنتجات / Product Search", 
                "🏪 البحث في المخازن / Warehouse Search",
                "📅 البحث بالتاريخ / Date Search", 
                "📊 التقارير والرسوم البيانية / Reports & Charts"
            ])
            
            with tab1:
                st.header("البحث في المنتجات / Product Search")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    search_product = st.selectbox(
                        "اختر المنتج / Select Product:",
                        [""] + products,
                        key="product_search",
                        help="اختر منتج للبحث عن كمياته في جميع المخازن"
                    )
                
                with col2:
                    filter_date = st.selectbox(
                        "تصفية بالتاريخ / Filter by Date:",
                        ["جميع التواريخ / All Dates"] + dates,
                        key="product_date_filter"
                    )
                
                if search_product:
                    # Filter data for selected product
                    product_data = data[data['Product'] == search_product].copy()
                    
                    if filter_date != "جميع التواريخ / All Dates":
                        product_data = product_data[product_data['Date'] == filter_date]
                    
                    if not product_data.empty:
                        st.subheader(f"تفاصيل المنتج / Product Details: {search_product}")
                        
                        # Display warehouse table
                        display_warehouse_table(product_data)
                        
                        # Show chart
                        fig = px.bar(
                            product_data.groupby('Warehouse')['Quantity'].sum().reset_index(),
                            x='Warehouse',
                            y='Quantity',
                            title=f"توزيع الكميات في المخازن / Quantity Distribution Across Warehouses",
                            labels={'Warehouse': 'المخزن / Warehouse', 'Quantity': 'الكمية / Quantity'}
                        )
                        fig.update_layout(xaxis_tickangle=-45, height=500)
                        st.plotly_chart(fig, use_container_width=True)
                        
                    else:
                        st.info("لا توجد بيانات للمنتج المختار في التاريخ المحدد / No data for selected product on specified date")
            
            with tab2:
                st.header("البحث في المخازن / Warehouse Search")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    search_warehouse = st.selectbox(
                        "اختر المخزن / Select Warehouse:",
                        [""] + warehouses,
                        key="warehouse_search"
                    )
                
                with col2:
                    min_quantity = st.number_input(
                        "الحد الأدنى للكمية / Minimum Quantity:",
                        min_value=0.0,
                        value=0.0,
                        key="min_qty"
                    )
                
                if search_warehouse:
                    warehouse_data = data[data['Warehouse'] == search_warehouse].copy()
                    
                    if min_quantity > 0:
                        warehouse_data = warehouse_data[warehouse_data['Quantity'] >= min_quantity]
                    
                    if not warehouse_data.empty:
                        st.subheader(f"منتجات المخزن / Warehouse Products: {search_warehouse}")
                        
                        # Display products in this warehouse
                        warehouse_summary = warehouse_data.groupby('Product')['Quantity'].sum().reset_index()
                        warehouse_summary = warehouse_summary.sort_values('Quantity', ascending=False)
                        
                        # Display as dataframe
                        st.dataframe(
                            warehouse_summary.rename(columns={
                                'Product': 'المنتج / Product',
                                'Quantity': 'الكمية / Quantity'
                            }),
                            use_container_width=True
                        )
                        
                        # Chart
                        if len(warehouse_summary) <= 20:  # Show chart only for reasonable number of products
                            fig = px.bar(
                                warehouse_summary.head(20),
                                x='Product',
                                y='Quantity',
                                title=f"أعلى المنتجات في {search_warehouse} / Top Products in {search_warehouse}"
                            )
                            fig.update_layout(xaxis_tickangle=-45, height=500)
                            st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                st.header("البحث بالتاريخ / Date Search")
                
                selected_date = st.selectbox(
                    "اختر التاريخ / Select Date:",
                    [""] + dates,
                    key="date_search"
                )
                
                if selected_date:
                    date_data = data[data['Date'] == selected_date].copy()
                    
                    if not date_data.empty:
                        st.subheader(f"تقرير المخزون بتاريخ / Inventory Report for: {selected_date}")
                        
                        # Summary by warehouse
                        warehouse_totals = date_data.groupby('Warehouse')['Quantity'].agg(['sum', 'count']).reset_index()
                        warehouse_totals.columns = ['المخزن / Warehouse', 'إجمالي الكمية / Total Quantity', 'عدد المنتجات / Product Count']
                        
                        st.dataframe(warehouse_totals, use_container_width=True)
                        
                        # Pie chart of warehouse distribution
                        fig = px.pie(
                            warehouse_totals,
                            values='إجمالي الكمية / Total Quantity',
                            names='المخزن / Warehouse',
                            title=f"توزيع المخزون بتاريخ {selected_date} / Inventory Distribution on {selected_date}"
                        )
                        st.plotly_chart(fig, use_container_width=True)
            
            with tab4:
                st.header("التقارير والرسوم البيانية / Reports & Charts")
                
                # Top products across all warehouses
                st.subheader("أعلى المنتجات كمية / Top Products by Quantity")
                top_products = data.groupby('Product')['Quantity'].sum().reset_index()
                top_products = top_products.sort_values('Quantity', ascending=False).head(20)
                
                fig = px.bar(
                    top_products,
                    x='Product',
                    y='Quantity',
                    title="أعلى 20 منتج بالكمية / Top 20 Products by Quantity"
                )
                fig.update_layout(xaxis_tickangle=-45, height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # Warehouse comparison
                st.subheader("مقارنة المخازن / Warehouse Comparison")
                warehouse_comparison = data.groupby('Warehouse')['Quantity'].agg(['sum', 'count']).reset_index()
                warehouse_comparison.columns = ['Warehouse', 'Total_Quantity', 'Product_Count']
                
                fig = px.scatter(
                    warehouse_comparison,
                    x='Product_Count',
                    y='Total_Quantity',
                    size='Total_Quantity',
                    hover_name='Warehouse',
                    title="مقارنة المخازن: عدد المنتجات مقابل الكمية الإجمالية / Warehouse Comparison: Product Count vs Total Quantity",
                    labels={'Product_Count': 'عدد المنتجات / Product Count', 'Total_Quantity': 'الكمية الإجمالية / Total Quantity'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Export functionality
                st.subheader("تصدير البيانات / Export Data")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("تصدير جميع البيانات / Export All Data"):
                        csv = data.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="تحميل CSV / Download CSV",
                            data=csv,
                            file_name=f"virginia_inventory_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if st.button("تصدير ملخص المخازن / Export Warehouse Summary"):
                        summary = data.groupby(['Warehouse'])['Quantity'].agg(['sum', 'count', 'mean']).reset_index()
                        csv = summary.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="تحميل ملخص المخازن / Download Summary",
                            data=csv,
                            file_name=f"warehouse_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                
                with col3:
                    if st.button("تصدير أعلى المنتجات / Export Top Products"):
                        csv = top_products.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="تحميل أعلى المنتجات / Download Top Products",
                            data=csv,
                            file_name=f"top_products_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                
        except Exception as e:
            st.error(f"خطأ في معالجة الملف / Error processing file: {e}")
            st.info("تأكد من أن الملف بصيغة CSV صحيحة / Please ensure the file is in correct CSV format")

if __name__ == "__main__":
    main()
