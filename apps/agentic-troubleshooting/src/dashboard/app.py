"""Streamlit dashboard for S3 Vector database visualization."""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
from vector_client import VectorClient

# Page config
st.set_page_config(
    page_title="K8s Memory Dashboard",
    page_icon="🧠",
    layout="wide"
)

# Initialize client
@st.cache_resource
def get_vector_client():
    return VectorClient()

def main():
    st.title("🧠 K8s Troubleshooting Memory Dashboard")
    st.markdown("Visualize and search your K8s troubleshooting knowledge base")
    
    client = get_vector_client()
    
    # Sidebar
    st.sidebar.header("Configuration")
    st.sidebar.info(f"**Bucket:** {client.vector_bucket_name}")
    st.sidebar.info(f"**Index:** {client.vector_index_name}")
    st.sidebar.info(f"**Region:** {client.aws_region}")
    
    # Danger zone in sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("⚠️ Danger Zone")
    
    # Initialize session state for confirmation
    if 'delete_confirmed' not in st.session_state:
        st.session_state.delete_confirmed = False
    
    # Confirmation checkbox
    st.session_state.delete_confirmed = st.sidebar.checkbox(
        "I understand this will delete ALL solutions", 
        value=st.session_state.delete_confirmed
    )
    
    # Delete button
    if st.sidebar.button("🗑️ Delete All Solutions", type="secondary", disabled=not st.session_state.delete_confirmed):
        with st.spinner("Deleting all solutions..."):
            success, message = client.delete_all_vectors()
        
        if success:
            st.sidebar.success(f"✅ {message}")
            st.cache_resource.clear()
            st.session_state.delete_confirmed = False
            st.rerun()
        else:
            st.sidebar.error(f"❌ {message}")
    
    # Main content
    col1, col2, col3 = st.columns(3)
    
    with col1:
        vector_count = client.get_vector_count()
        st.metric("Total Solutions", vector_count)
    
    with col2:
        st.metric("Index Name", client.vector_index_name)
    
    with col3:
        st.metric("AWS Region", client.aws_region)
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Search", "📋 All Solutions", "📊 Analytics"])
    
    with tab1:
        st.header("Search Solutions")
        
        query = st.text_input("Enter your K8s problem or question:")
        top_k = st.slider("Number of results", 1, 10, 5)
        
        if st.button("Search") and query:
            with st.spinner("Searching..."):
                results = client.search_vectors(query, top_k)
                
            if results:
                st.success(f"Found {len(results)} similar solutions")
                
                for i, result in enumerate(results, 1):
                    with st.expander(f"Solution {i} (Distance: {result.get('distance', 0):.3f})"):
                        metadata = result.get('metadata', {})
                        
                        st.markdown(f"**Problem:** {metadata.get('problem', 'N/A')}")
                        
                        content = metadata.get('content', '')
                        if content:
                            st.markdown("**Full Solution:**")
                            st.text_area("", content, height=200, key=f"solution_{i}")
                        
                        st.markdown(f"**Type:** {metadata.get('type', 'N/A')}")
                        st.markdown(f"**Key:** {result.get('key', 'N/A')}")
            else:
                st.warning("No similar solutions found")
    
    with tab2:
        st.header("All Stored Solutions")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Refresh Data"):
                st.cache_resource.clear()
                st.rerun()
        
        with st.spinner("Loading solutions..."):
            vectors = client.list_all_vectors()
        
        if vectors:
            # Create DataFrame for display
            data = []
            for vector in vectors:
                metadata = vector.get('metadata', {})
                data.append({
                    'Key': vector.get('key', 'N/A'),
                    'Problem': metadata.get('problem', 'N/A')[:100] + '...' if len(metadata.get('problem', '')) > 100 else metadata.get('problem', 'N/A'),
                    'Type': metadata.get('type', 'N/A'),
                    'Content Preview': metadata.get('content', 'N/A')[:150] + '...' if len(metadata.get('content', '')) > 150 else metadata.get('content', 'N/A')
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, width='stretch')
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"k8s_solutions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No solutions stored yet")
    
    with tab3:
        st.header("Analytics")
        
        vectors = client.list_all_vectors()
        
        if vectors:
            # Solution types distribution
            types = [v.get('metadata', {}).get('type', 'Unknown') for v in vectors]
            type_counts = pd.Series(types).value_counts()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Solution Types")
                st.bar_chart(type_counts)
            
            with col2:
                st.subheader("Storage Statistics")
                st.metric("Total Vectors", len(vectors))
                st.metric("Unique Types", len(type_counts))
                
                # Average content length
                content_lengths = [len(v.get('metadata', {}).get('content', '')) for v in vectors]
                avg_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
                st.metric("Avg Content Length", f"{avg_length:.0f} chars")
        else:
            st.info("No data available for analytics")

if __name__ == "__main__":
    main()