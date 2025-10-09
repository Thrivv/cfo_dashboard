import streamlit as st


def _generate_alert_question(alert):
    """Generate a specific question for the AI assistant based on the alert type"""
    alert_type = alert.get("title", "").lower()
    alert_message = alert.get("message", "")
    
    # Generate contextual questions based on alert type
    if "cash" in alert_type or "liquidity" in alert_type:
        return f"What should I do about our cash position and liquidity? {alert_message}"
    elif "leverage" in alert_type or "debt" in alert_type:
        return f"How can I improve our debt-to-equity ratio? {alert_message}"
    elif "performance" in alert_type or "revenue" in alert_type:
        return f"What strategies can help improve our financial performance? {alert_message}"
    elif "collections" in alert_type or "dso" in alert_type:
        return f"How can I optimize our accounts receivable and collections process? {alert_message}"
    elif "margins" in alert_type or "profitability" in alert_type:
        return f"What can I do to improve our profit margins? {alert_message}"
    elif "inventory" in alert_type:
        return f"How can I optimize our inventory management? {alert_message}"
    elif "operational" in alert_type or "efficiency" in alert_type:
        return f"What operational improvements should I focus on? {alert_message}"
    else:
        return f"Can you provide insights and recommendations about this alert: {alert_message}"


def render_cfo_alerts_section(latest_raw, raw_df):
    """
    Render CFO-specific alerts with new color scheme
    
    Args:
        latest_raw: Latest financial data row
        raw_df: Full financial data DataFrame
    
    Returns:
        None (renders directly to Streamlit)
    """
    # Get financial metrics
    cash_balance = latest_raw.get('Cash Balance', 0)
    debt_equity_ratio = latest_raw.get('Debt-to-Equity Ratio', 0)
    net_income = latest_raw.get('Net Income', 0)
    current_ratio = latest_raw.get('Current Ratio', 0)
    dso = latest_raw.get('Days Sales Outstanding (DSO)', 0)
    
    # Generate alerts
    cfo_alerts = []
    
    # High alerts (Critical) - #ba3a5e
    if cash_balance < 100000:
        cfo_alerts.append({
            "type": "CRITICAL",
            "title": "Cash Position",
            "message": "Critical cash shortage detected.",
            "severity": "critical"
        })
    if debt_equity_ratio > 0.8:
        cfo_alerts.append({
            "type": "CRITICAL", 
            "title": "Leverage",
            "message": "Debt-to-equity ratio critically high.",
            "severity": "critical"
        })
    if net_income < 0 and latest_raw.get('Year-over-Year Growth (%)', 0) < -10:
        cfo_alerts.append({
            "type": "CRITICAL",
            "title": "Performance", 
            "message": "Significant losses with declining growth.",
            "severity": "critical"
        })
    
    # Medium alerts (Warning) - #96ba3a
    if current_ratio < 1.5:
        cfo_alerts.append({
            "type": "WARNING",
            "title": "Liquidity",
            "message": "Current ratio below recommended threshold.",
            "severity": "warning"
        })
    if dso > 45:
        cfo_alerts.append({
            "type": "WARNING",
            "title": "Collections",
            "message": "DSO exceeds 45 days - review AR processes.",
            "severity": "warning"
        })
    if latest_raw.get('Gross Margin %', 0) < 30:
        cfo_alerts.append({
            "type": "WARNING",
            "title": "Margins",
            "message": "Gross margin below 30% - evaluate pricing strategy.",
            "severity": "warning"
        })
    
    # No alerts/Growth (Info) - #563aba
    if latest_raw.get('Year-over-Year Growth (%)', 0) > 10:
        cfo_alerts.append({
            "type": "INFO",
            "title": "Growth",
            "message": "Strong YoY growth above 10% - excellent performance.",
            "severity": "info"
        })
    if latest_raw.get('Gross Margin %', 0) > 40:
        cfo_alerts.append({
            "type": "INFO",
            "title": "Margins",
            "message": "Healthy gross margin above 40%.",
            "severity": "info"
        })
    if current_ratio > 2.0:
        cfo_alerts.append({
            "type": "INFO",
            "title": "Liquidity",
            "message": "Strong current ratio above 2.0 - good financial health.",
            "severity": "info"
        })
    
    # Render alerts with simple, non-scrolling design
    st.markdown("""
    <style>
    .alerts-simple-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    
    .alert-item {
        display: flex;
        align-items: center;
        padding: 12px 15px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 500;
        min-height: 50px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    
    .alert-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    
    .alert-critical {
        background: linear-gradient(135deg, #2d1b1b, #1a0f0f);
        color: white;
        border-left: 4px solid #e74c3c;
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #2d2a1b, #1a180f);
        color: white;
        border-left: 4px solid #f39c12;
    }
    
    .alert-info {
        background: linear-gradient(135deg, #1b1d2d, #0f111a);
        color: white;
        border-left: 4px solid #3498db;
    }
    
    .alert-icon {
        margin-right: 12px;
        font-size: 1.2rem;
    }
    
    .alert-text {
        flex: 1;
        line-height: 1.4;
    }
    
    .ask-KraYa-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-left: 10px;
        white-space: nowrap;
    }
    
    .ask-KraYa-btn:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    
    .alert-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Move "Active Alerts" title outside of columns
    st.subheader("Active Alerts")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if cfo_alerts:
            # No container - alerts display directly
            for i, alert in enumerate(cfo_alerts):
                if alert["severity"] == "critical":
                    alert_class = "alert-critical"
                    icon = ""
                elif alert["severity"] == "warning":
                    alert_class = "alert-warning"
                    icon = ""
                else:
                    alert_class = "alert-info"
                    icon = ""
                
                # Create columns for alert content and button
                alert_col1, alert_col2 = st.columns([4, 1])
                
                with alert_col1:
                    st.markdown(f'''
                    <div class="alert-item {alert_class}">
                        <div class="alert-content">
                            <div style="display: flex; align-items: center;">
                                <span class="alert-icon">{icon}</span>
                                <span class="alert-text">{alert["title"]}: {alert["message"]}</span>
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with alert_col2:
                    # Generate specific question for this alert
                    alert_question = _generate_alert_question(alert)
                    button_key = f"ask_KraYa_alert_{i}"
                    
                    if st.button("Ask to KraYa", key=button_key, help=f"Ask KraYa about: {alert['title']}"):
                        # Store the question and alert index for inline response
                        st.session_state.alert_question = alert_question
                        st.session_state.selected_alert_index = i
                        st.rerun()
        else:
            st.success("No active alerts - all metrics within acceptable ranges.")
    
    with col2:
        # Check if there's a selected alert and show LLM response
        if 'selected_alert_index' in st.session_state and 'alert_question' in st.session_state:
            selected_alert = cfo_alerts[st.session_state.selected_alert_index] if st.session_state.selected_alert_index < len(cfo_alerts) else None
            
            if selected_alert:
                # Get LLM response silently
                with st.spinner("KraYa analyzing..."):
                    try:
                        from services.chat_services import process_financial_question
                        llm_response = process_financial_question(st.session_state.alert_question)
                        
                        # Display the response in a styled container without titles
                        st.markdown("""
                          <style>
                          .KraYa-response {
                              background: #232738;
                              color: white;
                              padding: 15px;
                              border-radius: 12px;
                              margin: 5px 0 15px 0;
                              box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                              width: 100%;
                              min-height: 120px;
                              line-height: 1.8;
                              word-wrap: break-word;
                              white-space: normal;
                              font-size: 14px;
                          }
                          </style>
                          """, unsafe_allow_html=True)
                        
                        st.markdown(f'''
                        <div class="KraYa-response">
                            {llm_response}
                        </div>
                        ''', unsafe_allow_html=True)
                        
                        # Add a clear button
                        if st.button("Clear", key="clear_KraYa_response"):
                            if 'selected_alert_index' in st.session_state:
                                del st.session_state.selected_alert_index
                            if 'alert_question' in st.session_state:
                                del st.session_state.alert_question
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error getting response: {str(e)}")
                        st.info("Please try again or check the AI service connection.")
        else:
            # Show empty space when no alert is selected - no placeholder message
            st.markdown("""
            <div style="
                background: transparent;
                padding: 40px 20px;
                border-radius: 10px;
            ">
            </div>
            """, unsafe_allow_html=True)

