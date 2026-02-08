# در بخش CSS، این خطوط رو اضافه یا اصلاح کن:
st.markdown("""
<style>
    /* لجند کاملاً ترنسپرنت */
    .js-plotly-plot .plotly .legend {
        background-color: rgba(255, 255, 255, 0) !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* حذف هرگونه stroke از لجند */
    .js-plotly-plot .plotly .legend rect {
        stroke: none !important;
        stroke-opacity: 0 !important;
        fill-opacity: 0 !important;
    }
    
    /* متن لجند */
    .js-plotly-plot .plotly .legend .legendtext {
        font-weight: 500 !important;
        fill: #333333 !important;
    }
    
    /* عنوان لجند */
    .js-plotly-plot .plotly .legend .legendtitletext {
        font-weight: 600 !important;
        fill: #333333 !important;
    }
    
    /* بک‌گراند ترنسپرنت برای چارت‌ها */
    .js-plotly-plot .plotly,
    .js-plotly-plot .plotly .modebar,
    .js-plotly-plot .plotly .main-svg {
        background-color: transparent !important;
    }
    
    /* مخفی کردن المان‌های ناخواسته */
    .upload-section,
    [class*="upload"],
    .success-message {
        display: none !important;
    }
    
    /* بقیه CSS بدون تغییر... */
</style>
""", unsafe_allow_html=True)
