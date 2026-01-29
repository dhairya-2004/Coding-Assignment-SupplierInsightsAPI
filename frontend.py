import streamlit as st
import requests
import json

st.set_page_config(page_title="Supplier Insights", layout="wide")

API_URL = "http://127.0.0.1:8000"

st.title("Supplier Sourcing Insights")
st.markdown("Generate AI-powered procurement insights for supplier risk assessment")

st.header("Input Supplier Data")

category = st.text_input("Category", "IT Hardware")

st.subheader("Suppliers")

# Default data from assignment
default_suppliers = [
    {
        "supplier_name": "TechSource Inc.",
        "annual_spend_usd": 4200000,
        "on_time_delivery_pct": 92,
        "contract_expiry_months": 6,
        "single_source_dependency": True,
        "region": "North America"
    },
    {
        "supplier_name": "GlobalComp Solutions",
        "annual_spend_usd": 3100000,
        "on_time_delivery_pct": 85,
        "contract_expiry_months": 3,
        "single_source_dependency": False,
        "region": "Asia"
    },
    {
        "supplier_name": "NextGen Systems",
        "annual_spend_usd": 1800000,
        "on_time_delivery_pct": 97,
        "contract_expiry_months": 12,
        "single_source_dependency": False,
        "region": "Europe"
    }
]


num_suppliers = st.number_input("Number of Suppliers", min_value=1, max_value=10, value=3)

suppliers = []
for i in range(num_suppliers):
    st.markdown(f"**Supplier {i+1}**")
    col1, col2, col3 = st.columns(3)
    
    default = default_suppliers[i] if i < len(default_suppliers) else {}
    
    with col1:
        name = st.text_input(f"Name", default.get("supplier_name", f"Supplier {i+1}"), key=f"name_{i}")
        spend = st.number_input(f"Annual Spend ($)", value=default.get("annual_spend_usd", 1000000), key=f"spend_{i}")
    
    with col2:
        delivery = st.number_input(f"On-Time Delivery %", min_value=0, max_value=100, value=int(default.get("on_time_delivery_pct", 90)), key=f"delivery_{i}")
        expiry = st.number_input(f"Contract Expiry (months)", min_value=0, value=default.get("contract_expiry_months", 12), key=f"expiry_{i}")
    
    with col3:
        single_source = st.checkbox(f"Single Source?", value=default.get("single_source_dependency", False), key=f"single_{i}")
        region = st.selectbox(f"Region", ["North America", "Asia", "Europe", "South America", "Africa", "Australia"], 
                             index=["North America", "Asia", "Europe", "South America", "Africa", "Australia"].index(default.get("region", "North America")) if default.get("region") in ["North America", "Asia", "Europe", "South America", "Africa", "Australia"] else 0,
                             key=f"region_{i}")
    
    suppliers.append({
        "supplier_name": name,
        "annual_spend_usd": spend,
        "on_time_delivery_pct": delivery,
        "contract_expiry_months": expiry,
        "single_source_dependency": single_source,
        "region": region
    })
    
    st.divider()

# Generate
if st.button("Generate Insights", type="primary", use_container_width=True):
    with st.spinner("Analyzing suppliers..."):
        try:
            payload = {
                "category": category,
                "suppliers": suppliers
            }
            
            response = requests.post(
                f"{API_URL}/generate-insights",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                st.header("Analysis Results")
                
                risk_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Overall Risk Level", f"{risk_color.get(data['overall_risk_level'], '')} {data['overall_risk_level']}")
                
                with col2:
                    st.metric("Confidence Score", f"{data['confidence_score']:.0%}")
                
                st.subheader("Key Risks")
                for risk in data["key_risks"]:
                    st.error(risk)
                
                st.subheader("Negotiation Levers")
                for lever in data["negotiation_levers"]:
                    st.success(lever)

                st.subheader("Recommended Actions (Next 90 Days)")
                for i, action in enumerate(data["recommended_actions_next_90_days"], 1):
                    st.info(f"{i}. {action}")
                
                with st.expander("Raw JSON Response"):
                    st.json(data)
                    
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to API. Make sure the server is running at " + API_URL)
        except Exception as e:
            st.error(f"Error: {str(e)}")


st.markdown("---")
