import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import tempfile
import os
from typing import List, Dict, Optional
import re

# Configure page
st.set_page_config(
    page_title="Inventory Dashboard",
    page_icon="📦",
    layout="wide"
)

# Custom CSS for modern design
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
    .search-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
    }
    .stSelectbox > div > div {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

class SimpleInventoryProcessor:
    """Simple processor focused on your exact needs"""
    
    def __init__(self, df):
        self.raw_df = df.copy()
        self.processed_df = None
        
    def process_data(self):
        """Process CSV data to extract product quantities by location and date"""
        try:
            df = self.raw_df.copy()
            processed_data = []
            current_date = None
            
            # Get location columns - each Virtual Location is separate
            location_mapping = self._create_location_mapping(df.columns)
            
            for idx, row in df.iterrows():
                first_col = str(row.iloc[0]).strip()
                
                # Skip header rows
                if any(indicator in first_col for indicator in ['التعداد', 'الكمية', 'Column']):
                    continue
                
                # Check if this is a date row
                if self._is_date_row(first_col):
                    current_date = self._parse_date(first_col)
                    continue
                
                # Check if this is a product row
                if self._is_product_row(row, first_col):
                    product_data = self._extract_product_data(row, current_date, location_mapping)
                    if product_data:
                        processed_data.extend(product_data)
            
            if processed_data:
                self.processed_df = pd.DataFrame(processed_data)
                self._clean_data()
                return self.processed_df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Error processing data: {e}")
            return pd.DataFrame()
    
    def _create_location_mapping(self, columns):
        """Map each location to its column indices"""
        mapping = {}
        
        # Define all possible locations including Virtual Locations separately
        locations = [
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
        
        for i, col in enumerate(columns):
            col_str = str(col)
            for location in locations:
                if location in col_str:
                    clean_name = self._clean_location_name(location)
                    # Assume count column is current, quantity column is next
                    if i + 1 < len(columns):
                        mapping[clean_name] = (i, i + 1)
                    break
        
        return mapping
    
    def _clean_location_name(self, location):
        """Clean location names"""
        if '/' in location:
            return location.split('/')[-1]
        return location
    
    def _is_date_row(self, text):
        """Check if row contains date"""
        if not text or text == 'nan':
            return False
        
        date_patterns = [
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}',
            r'(June|July|August|September|October|November|December)\s+\d{4}'
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
    
    def _parse_date(self, date_string):
        """Parse date string"""
        try:
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
        """Check if row contains product"""
        if not first_col or first_col == 'nan':
            return False
        
        # Look for product code or Arabic text with data
        has_product_code = re.search(r'\[\d+\]', first_col)
        has_arabic = any('\u0600' <= char <= '\u06FF' for char in first_col)
        has_data = any(self._safe_float(val) > 0 for val in row.iloc[1:] if not pd.isna(val))
        
        return has_product_code or (has_arabic and has_data)
    
    def _extract_product_data(self, row, current_date, location_mapping):
        """Extract product data for each location"""
        try:
            product_name = str(row.iloc[0]).strip()
            if not product_name or product_name == 'nan':
                return []
            
            data_points = []
            
            for location_name, (count_idx, quantity_idx) in location_mapping.items():
                count_val = 0
                quantity_val = 0
                
                if count_idx < len(row):
                    count_val = self._safe_float(row.iloc[count_idx])
                
                if quantity_idx < len(row):
                    quantity_val = self._safe_float(row.iloc[quantity_idx])
                
                # Only add if there's meaningful data
                if count_val > 0 or quantity_val > 0:
                    data_points.append({
                        'Product': product_name,
                        'Date': current_date or 'Unknown',
                        'Location': location_name,
                        'Count': count_val,
                        'Quantity': quantity_val
                    })
            
            return data_points
            
        except Exception as e:
            return []
    
    def _safe_float(self, value):
        """Convert value to float safely"""
        try:
            if pd.isna(value):
                return 0.0
            str_val = str(value).replace(',', '').strip()
            return float(str_val) if str_val and str_val != 'nan' else 0.0
        except:
            return 0.0
    
    def _clean_data(self):
        """Clean processed data"""
        if self.processed_df is not None and not self.processed_df.empty:
            # Remove rows with no data
            self.processed_df = self.processed_df[
                (self.processed_df['Quantity'] > 0) | (self.processed_df['Count'] > 0)
            ]
            
            # Clean product names
            self.processed_df['Product'] = self.processed_df['Product'].str.strip()
            
            # Sort data
            self.processed_df = self.processed_df.sort_values(['Date', 'Product', 'Location'])

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

def main():
    st.title("📦 Simple Inventory Dashboard")
    st.markdown("**Search products, track quantities across all locations and dates**")
    
    # File upload
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload your inventory CSV file", type=['csv'])
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_file is not None:
        try:
            # Process data
            with st.spinner("Processing your inventory data..."):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
                processor = SimpleInventoryProcessor(df)
                data = processor.process_data()
            
            if data.empty:
                st.error("❌ No data could be processed from your file")
                return
            
            st.success(f"✅ Processed {len(data)} inventory records")
            
            # Get unique values for filters
            products = sorted(data['Product'].unique().tolist())
            locations = sorted(data['Location'].unique().tolist()) 
            dates = sorted(data['Date'].unique().tolist())
            
            # Main functionality tabs
            tab1, tab2, tab3 = st.tabs(["🔍 Product Search", "📅 Date Search", "📊 Export & Charts"])
            
            with tab1:
                st.header("Search Product")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    search_product = st.selectbox("Select Product:", [""] + products, key="product_search")
                
                with col2:
                    filter_date = st.selectbox("Filter by Date (Optional):", ["All Dates"] + dates, key="product_date_filter")
                
                if search_product:
                    # Filter data
                    product_data = data[data['Product'] == search_product].copy()
                    
                    if filter_date != "All Dates":
                        product_data = product_data[product_data['Date'] == filter_date]
                    
                    if not product_data.empty:
                        # Show metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            total_qty = product_data['Quantity'].sum()
                            st.markdown(f"""
                            <div class="metric-card">
                                <p class="metric-value">{format_number(total_qty)}</p>
                                <p class="metric-label">Total Quantity</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            total_count = product_data['Count'].sum()
                            st.markdown(f"""
                            <div class="metric-card">
                                <p class="metric-value">{format_number(total_count)}</p>
                                <p class="metric-label">Total Count</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            locations_count = len(product_data['Location'].unique())
                            st.markdown(f"""
                            <div class="metric-card">
                                <p class="metric-value">{locations_count}</p>
                                <p class="metric-label">Locations</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col4:
                            dates_count = len(product_data['Date'].unique())
                            st.markdown(f"""
                            <div class="metric-card">
                                <p class="metric-value">{dates_count}</p>
                                <p class="metric-label">Date Entries</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Location breakdown chart
                        st.subheader("📍 Quantity by Location")
                        location_summary = product_data.groupby('Location')['Quantity'].sum().sort_values(ascending=False)
                        
                        if not location_summary.empty:
                            fig = px.bar(
                                x=location_summary.values,
                                y=location_summary.index,
                                orientation='h',
                                title=f"Quantity Distribution for {search_product}",
                                labels={'x': 'Quantity', 'y': 'Location'}
                            )
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Date timeline if multiple dates
                        if len(product_data['Date'].unique()) > 1:
                            st.subheader("📈 Quantity Timeline")
                            timeline_data = product_data.groupby(['Date', 'Location'])['Quantity'].sum().reset_index()
                            
                            fig2 = px.line(
                                timeline_data, 
                                x='Date', 
                                y='Quantity', 
                                color='Location',
                                title=f"Quantity Over Time for {search_product}",
                                markers=True
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                        
                        # Data table
                        st.subheader("📋 Detailed Data")
                        st.dataframe(product_data, use_container_width=True)
                    
                    else:
                        st.info("No data found for the selected product and date filter.")
            
            with tab2:
                st.header("Search by Date")
                
                selected_date = st.selectbox("Select Date:", dates, key="date_search")
                
                if selected_date:
                    date_data = data[data['Date'] == selected_date].copy()
                    
                    if not date_data.empty:
                        # Show metrics for the date
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            total_products = len(date_data['Product'].unique())
                            st.markdown(f"""
                            <div class="metric-card">
                                <p class="metric-value">{total_products}</p>
                                <p class="metric-label">Products</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            total_qty = date_data['Quantity'].sum()
                            st.markdown(f"""
                            <div class="metric-card">
                                <p class="metric-value">{format_number(total_qty)}</p>
                                <p class="metric-label">Total Quantity</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            total_count = date_data['Count'].sum()
                            st.markdown(f"""
                            <div class="metric-card">
                                <p class="metric-value">{format_number(total_count)}</p>
                                <p class="metric-label">Total Count</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col4:
                            total_locations = len(date_data['Location'].unique())
                            st.markdown(f"""
                            <div class="metric-card">
                                <p class="metric-value">{total_locations}</p>
                                <p class="metric-label">Locations</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Top products for this date
                        st.subheader("🏆 Top Products by Quantity")
                        top_products = date_data.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(10)
                        
                        if not top_products.empty:
                            fig = px.bar(
                                x=top_products.values,
                                y=top_products.index,
                                orientation='h',
                                title=f"Top Products on {selected_date}"
                            )
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Location distribution for this date
                        st.subheader("📍 Location Distribution")
                        location_dist = date_data.groupby('Location')['Quantity'].sum().sort_values(ascending=False)
                        
                        if not location_dist.empty:
                            fig2 = px.pie(
                                values=location_dist.values,
                                names=location_dist.index,
                                title=f"Quantity Distribution by Location on {selected_date}"
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                        
                        # All transactions for this date
                        st.subheader("📋 All Transactions")
                        st.dataframe(date_data, use_container_width=True)
                    
                    else:
                        st.info(f"No data found for {selected_date}")
            
            with tab3:
                st.header("Export & Charts")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Generate Charts")
                    
                    chart_type = st.selectbox("Select Chart Type:", [
                        "Top 10 Products Overall",
                        "Location Distribution", 
                        "Inventory Timeline",
                        "Product Comparison"
                    ])
                    
                    if st.button("Generate Chart"):
                        if chart_type == "Top 10 Products Overall":
                            top_products = data.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(10)
                            fig = px.bar(x=top_products.values, y=top_products.index, orientation='h',
                                       title="Top 10 Products by Total Quantity")
                            st.plotly_chart(fig, use_container_width=True)
                        
                        elif chart_type == "Location Distribution":
                            location_totals = data.groupby('Location')['Quantity'].sum()
                            fig = px.pie(values=location_totals.values, names=location_totals.index,
                                       title="Total Quantity Distribution by Location")
                            st.plotly_chart(fig, use_container_width=True)
                        
                        elif chart_type == "Inventory Timeline":
                            timeline = data.groupby('Date')['Quantity'].sum().reset_index()
                            fig = px.line(timeline, x='Date', y='Quantity', 
                                        title="Total Inventory Over Time", markers=True)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        elif chart_type == "Product Comparison":
                            selected_products = st.multiselect("Select Products to Compare:", products)
                            if selected_products:
                                comp_data = data[data['Product'].isin(selected_products)]
                                comp_summary = comp_data.groupby(['Product', 'Location'])['Quantity'].sum().reset_index()
                                fig = px.bar(comp_summary, x='Location', y='Quantity', color='Product',
                                           title="Product Comparison by Location")
                                st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.subheader("📤 Export Data")
                    
                    export_option = st.selectbox("Select Export Option:", [
                        "Complete Dataset",
                        "Product Summary",
                        "Location Summary",
                        "Date Summary"
                    ])
                    
                    if st.button("Generate Export"):
                        if export_option == "Complete Dataset":
                            export_data = data
                        elif export_option == "Product Summary":
                            export_data = data.groupby('Product').agg({
                                'Quantity': ['sum', 'mean', 'count'],
                                'Count': 'sum',
                                'Location': 'nunique',
                                'Date': 'nunique'
                            }).round(2)
                        elif export_option == "Location Summary":
                            export_data = data.groupby('Location').agg({
                                'Quantity': ['sum', 'mean', 'count'],
                                'Count': 'sum', 
                                'Product': 'nunique',
                                'Date': 'nunique'
                            }).round(2)
                        else:  # Date Summary
                            export_data = data.groupby('Date').agg({
                                'Quantity': ['sum', 'mean', 'count'],
                                'Count': 'sum',
                                'Product': 'nunique',
                                'Location': 'nunique'
                            }).round(2)
                        
                        # Create download buttons
                        csv_data = export_data.to_csv(index=True)
                        excel_buffer = io.BytesIO()
                        export_data.to_excel(excel_buffer, index=True, engine='openpyxl')
                        excel_buffer.seek(0)
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.download_button(
                                label="📄 Download CSV",
                                data=csv_data,
                                file_name=f"{export_option.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        
                        with col_b:
                            st.download_button(
                                label="📊 Download Excel", 
                                data=excel_buffer,
                                file_name=f"{export_option.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        
                        st.success("✅ Export ready for download!")
                        st.dataframe(export_data.head(), use_container_width=True)
        
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
    
    else:
        # Welcome screen
        st.markdown("""
        ## 🎯 What This Dashboard Does:
        
        **📦 Product Search:**
        - Search any product and see ALL its quantities across ALL locations
        - Filter by specific dates to see quantities on that date
        - View charts showing distribution across locations
        
        **📅 Date Search:** 
        - Pick any date and see ALL products and transactions for that date
        - View all inventory levels across all locations for that date
        - See charts of top products and location distribution
        
        **📊 Export & Charts:**
        - Generate various charts and visualizations
        - Export data as CSV or Excel files
        - Compare products across locations
        
        **✨ Features:**
        - Each Virtual Location is tracked separately (تذوق, عينات, مستلزمات, هالك)
        - Handles Arabic product names perfectly
        - Modern, clean interface
        - Fast search and filtering
        """)

if __name__ == "__main__":
    main()