import streamlit as st
import pandas as pd
import io
import datetime

# --- Configuration & Setup ---
st.set_page_config(
    page_title="SpendWise - Financial Manager",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the SpendWise look and feel (simulating index.css/manager.css)
st.markdown("""
<style>
/* Header styling */
.css-h5aa2j {
    background-color: #d9534f;
    color: white;
    padding: 30px 0;
    font-size: 32px;
    font-weight: bold;
    text-align: center;
    position: sticky;
    top: 0;
    z-index: 1000;
}
.css-h5aa2j h1 {
    color: white !important;
    margin: 0;
    font-size: 32px;
}
/* Card styling */
div.st-emotion-cache-1r4r9wr { /* Targets the main column block */
    padding: 10px;
}
.st-emotion-cache-vj1n9y { /* Targets markdown card background */
    background-color: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    margin-bottom: 20px;
}
/* Spending metrics */
[data-testid="metric-container"] {
    background-color: #f5f0f0;
    border: 1px solid #d9534f;
    padding: 15px 20px;
    border-radius: 10px;
    color: #d9534f;
    overflow-wrap: break-word;
}
</style>
""", unsafe_allow_html=True)


# --- Utility Functions ---

def get_week_of_month(date):
    """Calculates the approximate week number within a month."""
    return (date.day - 1) // 7 + 1

def parse_data(uploaded_file):
    """Reads the uploaded CSV and prepares the DataFrame."""
    try:
        data = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        df = pd.read_csv(data)
        
        # Data Cleaning and Enhancement
        df.columns = [col.strip() for col in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df.dropna(subset=['Date', 'Amount'], inplace=True)
        
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month
        df['MonthName'] = df['Date'].dt.strftime('%B')
        df['WeekOfMonth'] = df['Date'].apply(get_week_of_month)
        
        # Filter out negative amounts (which typically represent income/credits, we focus on positive spending)
        df_spent = df[df['Amount'] > 0].copy()
        
        # Exclude Savings and Income from the 'spent' calculation for analysis
        df_spent = df_spent[~df_spent['Category'].isin(['Savings', 'Income'])].copy()
        
        return df_spent
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None

# --- UI Components (Streamlit Pages) ---

def show_upload_page():
    """Renders the file upload screen."""
    st.title("SpendWise")
    st.subheader("Upload Your Bank Statement (CSV only)")
    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'], key="uploader")
    
    if uploaded_file is not None:
        # Save the uploaded file in session state for access across pages
        st.session_state['df_spent'] = parse_data(uploaded_file)
        
        if st.session_state['df_spent'] is not None:
            st.success("File uploaded and parsed successfully! Switch to the 'Manage' or 'Analyze' page.")
    else:
         st.session_state['df_spent'] = None

def get_date_filters(df):
    """Creates sidebar filters for year and month."""
    unique_years = sorted(df['Year'].unique(), reverse=True)
    
    # Determine default selection (latest period)
    latest_year = unique_years[0]
    latest_month_num = df[df['Year'] == latest_year]['Month'].max()
    latest_month_name = df[df['Month'] == latest_month_num]['MonthName'].iloc[0]

    # Create selectors
    selected_year = st.sidebar.selectbox("Select Year:", unique_years, index=0)
    
    months_in_year = df[df['Year'] == selected_year]['MonthName'].unique()
    # Use latest month as default index if it exists in the current year's months
    try:
        default_month_index = list(months_in_year).index(latest_month_name)
    except:
        default_month_index = 0 # Fallback to first month
        
    selected_month_name = st.sidebar.selectbox("Select Month:", months_in_year, index=default_month_index)
    
    # Filter the DataFrame
    df_filtered = df[
        (df['Year'] == selected_year) & 
        (df['MonthName'] == selected_month_name)
    ]
    return df_filtered, selected_year, selected_month_name


def show_manage_page():
    """Renders the monthly summary and savings tips."""
    st.markdown("<h1>SpendWise</h1>", unsafe_allow_html=True)
    
    if st.session_state.get('df_spent') is None:
        st.warning("⚠️ Please go to the 'Upload' page to load your bank statement first.")
        return

    df_spent = st.session_state['df_spent']
    df_filtered, selected_year, selected_month_name = get_date_filters(df_spent)

    total_spent = df_filtered['Amount'].sum()
    suggested_savings = total_spent * 0.2
    
    st.subheader(f"Monthly Summary ({selected_month_name} {selected_year})")

    # Display Metrics (Cards)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Spent This Month:", f"${total_spent:,.2f}")
    with col2:
        st.metric("Suggested Savings (20%):", f"${suggested_savings:,.2f}")

    st.markdown("---")

    # Display Savings Tip (Tip Box)
    st.subheader("💡 Saving Tip:")
    suggestions = [
        "Cut down on eating out – cook at home more often.",
        "Cancel unused subscriptions.",
        "Use public transport instead of cabs.",
        "Track daily expenses to spot wasteful spending.",
        "Save at least 20% of income before spending."
    ]
    # Simple randomized display for the tip
    tip_df = pd.DataFrame({'Tip': suggestions})
    st.info(tip_df.sample(1).iloc[0, 0])


def show_analyze_page():
    """Renders the analysis (charts and raw data table)."""
    st.markdown("<h1>SpendWise</h1>", unsafe_allow_html=True)
    
    if st.session_state.get('df_spent') is None:
        st.warning("⚠️ Please go to the 'Upload' page to load your bank statement first.")
        return

    df_spent = st.session_state['df_spent']
    df_filtered, selected_year, selected_month_name = get_date_filters(df_spent)
    
    st.subheader(f"Data Analysis ({selected_month_name} {selected_year})")
    
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Pie Chart (Category Spending)")
        if not df_filtered.empty:
            # Aggregate data for Pie Chart
            pie_data = df_filtered.groupby('Category')['Amount'].sum().reset_index()
            # Streamlit uses Altair for charts; this creates a simple pie/donut chart
            st.bar_chart(pie_data, x='Category', y='Amount', color='#d9534f') # Using bar chart as a simple visual alternative
            # You can also use st.dataframe(pie_data) to show the raw data
        else:
            st.info("No spending data for this period.")

    with col2:
        st.markdown("### Weekly Graph (Spending Trends)")
        if not df_filtered.empty:
            # Aggregate data for Weekly Graph
            weekly_data = df_filtered.groupby('WeekOfMonth')['Amount'].sum().reset_index()
            weekly_data['Week'] = 'Week ' + weekly_data['WeekOfMonth'].astype(str)
            
            st.line_chart(weekly_data, x='Week', y='Amount', color='#5cb85c')
        else:
            st.info("No spending data for this period.")

    st.markdown("---")
    st.markdown("### Bank Statement (Filtered Data)")
    
    # Display the filtered statement table
    if not df_filtered.empty:
        # Display only relevant columns for a clean table view
        st.dataframe(df_filtered[['Date', 'Category', 'Amount']].sort_values(by='Date'), 
                     use_container_width=True, 
                     hide_index=True)
    else:
        st.info("No transactions found for the selected period.")


# --- Main App Logic (Navigation) ---

def main():
    # Streamlit sidebar handles navigation
    st.sidebar.title("SpendWise Navigation")
    
    page = st.sidebar.radio(
        "Go to:", 
        ("Upload", "Manage", "Analyze")
    )

    # Display the selected page
    if page == "Upload":
        show_upload_page()
    elif page == "Manage":
        show_manage_page()
    elif page == "Analyze":
        show_analyze_page()

if __name__ == "__main__":
    main()