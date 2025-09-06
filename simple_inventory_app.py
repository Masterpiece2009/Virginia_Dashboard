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
            
            # Map each warehouse to its quantity column (skip count columns)
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
        Map each warehouse to its quantity column (skip count columns).
        Assumes that for each warehouse, the quantity column is the first numeric column after the warehouse name,
        and the next column is the count column (which we skip).
        """
        mapping = {}
        for warehouse in warehouses:
            for i, col in enumerate(columns):
                col_str = str(col)
                if warehouse in col_str:
                    qty_idx = i + 1
                    # Defensive: Only map if this is not a filler/colour column and is within range
                    if qty_idx < len(columns):
                        # Optional: You can add further checks here to confirm it's the quantity column
                        mapping[warehouse.split('/')[-1] if '/' in warehouse else warehouse] = qty_idx
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
        
        # Look for product code or Arabic text with data
        has_product_code = re.search(r'\[\d+\]', first_col)
        has_arabic = any('\u0600' <= char <= '\u06FF' for char in first_col)
        has_data = any(self._to_float(val) > 0 for val in row.iloc[1:] if not pd.isna(val))
        
        return has_product_code or (has_arabic and has_data)
    
    def _extract_quantities(self, row, current_date, warehouse_mapping):
        """Extract product quantities from each warehouse - use only mapped quantity columns"""
        try:
            product_name = str(row.iloc[0]).strip()
            if not product_name or product_name == 'nan':
                return []
            
            data_points = []
            
            for warehouse_name, quantity_idx in warehouse_mapping.items():
                if quantity_idx < len(row):
                    # Get the exact quantity from the sheet (skip the count column)
                    quantity = self._to_float(row.iloc[quantity_idx])
                    
                    # Only add if there's quantity (show exact number from sheet)
                    if quantity > 0:
                        data_points.append({
                            'Product': product_name,
                            'Date': current_date or 'Unknown',
                            'Location': warehouse_name,
                            'Quantity': quantity  # Exact number from sheet
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
    st.markdown("**Track product quantities across all warehouse locations**")
    
    # File upload
    uploaded_file = st.file_uploader("Upload your inventory CSV file", type=['csv'])
    
    if uploaded_file:
        try:
            # Process data
            with st.spinner("Processing inventory data..."):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
                processor = InventoryProcessor(df)
                data = processor.process_data()
            
            if data.empty:
                st.error("No data found in file")
                return
            
            st.success(f"Loaded {len(data)} inventory records")
            
            # Get unique values
            products = sorted(data['Product'].unique())
            warehouses = sorted(data['Location'].unique())
            dates = sorted(data['Date'].unique())
            
            # Main tabs
            tab1, tab2, tab3 = st.tabs(["Product Search", "Date Search", "Export Data"])
            
            with tab1:
                st.header("Search Product")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    selected_product = st.selectbox("Select Product:", [""] + products, key="product_search")
                
                with col2:
                    date_filter = st.selectbox("Filter by Date:", ["All Dates"] + dates, key="product_date")
                
                if selected_product:
                    # Filter data
                    product_data = data[data['Product'] == selected_product].copy()
                    
                    if date_filter != "All Dates":
                        product_data = product_data[product_data['Date'] == date_filter]
                    
                    if not product_data.empty:
                        st.markdown(f"### {selected_product}")
                        
                        # Summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            total_qty = product_data['Quantity'].sum()
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{format_number(total_qty)}</div>
                                <div class="metric-text">Total Quantity</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            warehouse_count = len(product_data['Location'].unique())
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{warehouse_count}</div>
                                <div class="metric-text">Warehouses</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            date_count = len(product_data['Date'].unique())
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{date_count}</div>
                                <div class="metric-text">Date Entries</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col4:
                            avg_qty = product_data['Quantity'].mean()
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{format_number(avg_qty)}</div>
                                <div class="metric-text">Average Quantity</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Show quantities by warehouse - exact numbers from sheet
                        st.subheader("Quantity by Warehouse")
                        warehouse_summary = product_data.groupby('Location')['Quantity'].sum().sort_values(ascending=False)
                        
                        if not warehouse_summary.empty:
                            # Show each warehouse with exact quantity
                            for location, quantity in warehouse_summary.items():
                                st.markdown(f"""
                                <div class="warehouse-row">
                                    <div class="warehouse-name">{location}</div>
                                    <div class="warehouse-quantity">{quantity:,.2f}</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Simple chart
                            st.bar_chart(warehouse_summary)
                        
                        # Timeline if multiple dates
                        if len(product_data['Date'].unique()) > 1:
                            st.subheader("Quantity Timeline")
                            timeline_data = product_data.groupby('Date')['Quantity'].sum().reset_index()
                            st.line_chart(timeline_data.set_index('Date'))
                        
                        # Data table showing exact values
                        st.subheader("Detailed Data")
                        display_data = product_data[['Date', 'Location', 'Quantity']].copy()
                        st.dataframe(display_data, use_container_width=True)
                    
                    else:
                        st.info("No data found for selected product and date filter")
            
            with tab2:
                st.header("Search by Date")
                
                selected_date = st.selectbox("Select Date:", dates, key="date_search")
                
                if selected_date:
                    date_data = data[data['Date'] == selected_date].copy()
                    
                    if not date_data.empty:
                        st.markdown(f"### {selected_date}")
                        
                        # Date metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            total_products = len(date_data['Product'].unique())
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{total_products}</div>
                                <div class="metric-text">Products</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            total_qty = date_data['Quantity'].sum()
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{format_number(total_qty)}</div>
                                <div class="metric-text">Total Quantity</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            total_warehouses = len(date_data['Location'].unique())
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{total_warehouses}</div>
                                <div class="metric-text">Warehouses</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col4:
                            avg_per_product = total_qty / total_products if total_products > 0 else 0
                            st.markdown(f"""
                            <div class="metric-box">
                                <div class="metric-number">{format_number(avg_per_product)}</div>
                                <div class="metric-text">Avg per Product</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Top products
                        st.subheader("Top Products by Quantity")
                        top_products = date_data.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(10)
                        
                        if not top_products.empty:
                            st.bar_chart(top_products)
                        
                        # Warehouse distribution - show exact quantities
                        st.subheader("Warehouse Distribution")
                        warehouse_dist = date_data.groupby('Location')['Quantity'].sum().sort_values(ascending=False)
                        
                        if not warehouse_dist.empty:
                            # Show exact quantities per warehouse
                            for location, quantity in warehouse_dist.items():
                                st.markdown(f"""
                                <div class="warehouse-row">
                                    <div class="warehouse-name">{location}</div>
                                    <div class="warehouse-quantity">{quantity:,.2f}</div>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # All transactions  
                        st.subheader("All Transactions")
                        display_data = date_data[['Product', 'Location', 'Quantity']].copy()
                        st.dataframe(display_data, use_container_width=True)
                    
                    else:
                        st.info(f"No data found for {selected_date}")
            
            with tab3:
                st.header("Export Data")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Quick Charts")
                    
                    chart_type = st.selectbox("Select Chart:", [
                        "Top 10 Products",
                        "Warehouse Distribution", 
                        "Quantity Timeline"
                    ])
                    
                    if st.button("Show Chart"):
                        if chart_type == "Top 10 Products":
                            top_products = data.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(10)
                            st.bar_chart(top_products)
                        
                        elif chart_type == "Warehouse Distribution":
                            warehouse_totals = data.groupby('Location')['Quantity'].sum().sort_values(ascending=False)
                            st.bar_chart(warehouse_totals)
                        
                        elif chart_type == "Quantity Timeline":
                            timeline = data.groupby('Date')['Quantity'].sum().reset_index()
                            st.line_chart(timeline.set_index('Date'))
                
                with col2:
                    st.subheader("Export Options")
                    
                    export_option = st.selectbox("Select Export:", [
                        "Complete Dataset",
                        "Product Summary",
                        "Warehouse Summary",
                        "Date Summary"
                    ])
                    
                    if st.button("Generate Export"):
                        if export_option == "Complete Dataset":
                            export_data = data
                        elif export_option == "Product Summary":
                            export_data = data.groupby('Product').agg({
                                'Quantity': ['sum', 'mean', 'count'],
                                'Location': 'nunique',
                                'Date': 'nunique'
                            }).round(2)
                        elif export_option == "Warehouse Summary":
                            export_data = data.groupby('Location').agg({
                                'Quantity': ['sum', 'mean', 'count'],
                                'Product': 'nunique',
                                'Date': 'nunique'
                            }).round(2)
                        else:  # Date Summary
                            export_data = data.groupby('Date').agg({
                                'Quantity': ['sum', 'mean', 'count'],
                                'Product': 'nunique',
                                'Location': 'nunique'
                            }).round(2)
                        
                        # Download options
                        csv_data = export_data.to_csv(index=True, encoding='utf-8-sig')
                        excel_buffer = io.BytesIO()
                        export_data.to_excel(excel_buffer, index=True, engine='openpyxl')
                        excel_buffer.seek(0)
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.download_button(
                                label="Download CSV",
                                data=csv_data,
                                file_name=f"{export_option.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        
                        with col_b:
                            st.download_button(
                                label="Download Excel", 
                                data=excel_buffer,
                                file_name=f"{export_option.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        
                        st.success("Export ready for download!")
                        st.dataframe(export_data.head(10), use_container_width=True)
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    
    else:
        # Welcome screen
        st.markdown("""

        """)

if __name__ == "__main__":
    main()
