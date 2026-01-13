import pandas as pd
import streamlit as st
import plotly.express as px

# -----------------------------
# Config
# -----------------------------
FILE_PATH = "Core15 D2C Survey.xlsx"

DEMOGRAPHIC_COLS = [
    "How many years of professional experience do you have?",
    "Which best describes your current role?",
    "What is your gender?",
]

# Allowed answers for each question. Anything else gets bucketed to "other".
ALLOWED = {
    # section 1
    "In the last 6 months, have you experienced any of the following?": [
        "Missed a promotion or opportunity",
        "Received critical feedback about leadership or influence",
        "Felt ineffective managing others",
        "Struggled with conflict or alignment",
        "Felt stuck despite strong technical skills",
        "None of the above",
    ],
    "Which of the following do you believe most contributed to these outcomes?": [
        "Gaps in my leadership or interpersonal skills",
        "Lack of clear feedback or expectations",
        "Organizational politics or bias",
        "Limited opportunity or timing",
        "I'm not sure what the real cause is",
        "Other (open text)",
    ],
    "Which of these best describes your current motivation to improve leadership skills?": [
        "I am actively trying to improve right now",
        "I know I should improve, but haven't taken action",
        "It matters, but not urgent",
        "Not a priority for me",
    ],

    # section 2
    "In the last 12 months, how much have you personally spent on professional or leadership development?": [
        "0",
        "<$100",
        "$100-$500",
        "$500-$1,500",
        "$1,500+",
    ],
    "What best explains the reason for your spending on leadership development over the past 12 months?": [
        "My employer typically pays for this",
        "I didn't actively look for solutions",
        "I looked, but didn't find anything credible",
        "I found options, but they felt too expensive",
        "I don't usually pay for self-development",
        "Other (open text)",
    ],
    "What have you personally paid for?": [
        "Online course",
        "Assessment or personality test",
        "Coaching (group or 1:1)",
        "Books or learning subscriptions",
        "Nothing paid personally",
    ],
    "If a leadership assessment + personalized training system clearly improved your effectiveness as a leader, what would feel like a reasonable monthly price?": [
        "0",
        "$10-$25",
        "$25-$50",
        "$50-$100",
        "$100+",
    ],
    "When it comes to leadership or professional development, I generally expect:": [
        "My Employer to pay",
        "A mix of employer and personal spending",
        "To pay myself",
    ],

    # section 3
    "Have you ever used a leadership or personality assessment that was NOT required by an employer?": [
        "Yes",
        "No",
    ],
    "Which sources do you take feedback on your capabilities from seriously?": [
        "Manager",
        "Peers",
        "Coach or Mentor",
        "Assessment tools",
        "Self-reflection only",
        "I generally distrust feedback",
    ],
    "Seeing my leadership skills benchmarked against others would feel:": [
        "Motivating",
        "Interesting but neutral",
        "Anxiety-inducing",
        "Not useful",
        "Actively discouraging",
    ],

    # section 4
    "Think about the last self-improvement effort you started on your own. What happened?": [
        "I stuck with it consistently",
        "I stayed engaged for a while, then dropped off",
        "I barely got started",
        "I avoid self-directed programs",
    ],
    "What most often causes you to stop engaging with self-development tools?": [
        "Time constraints",
        "Lack of accountability",
        "Content wasn't relevant",
        "Hard to see progress",
        "Lost motivation",
        "Cost",
        "Other",
    ],
    "What would most increase your likelihood of sticking with a leadership development system?": [
        "Clear progress tracking",
        "Personalized recommendations",
        "Social comparison or benchmarks",
        "External accountability (coach, group)",
        "Short, lightweight activities",
    ],

    # section 6 demographics
    "How many years of professional experience do you have?": [
        "0-3",
        "4-7",
        "8-15",
        "16+",
    ],
    "Which best describes your current role?": [
        "Individual Contributor",
        "People Manager",
        "Senior Leader",
        "Founder/Executive",
    ],
    "What is your gender?": [
        "Male",
        "Female",
        "Prefer not to say",
    ],
}

# Which questions are multi-select (comma-separated)
MULTI_SELECT = {
    "In the last 6 months, have you experienced any of the following?",
    "What have you personally paid for?",
    "Which sources do you take feedback on your capabilities from seriously?",
    "What most often causes you to stop engaging with self-development tools?",
}

OTHER_LABEL = "other"


# -----------------------------
# Helpers
# -----------------------------
def bucket_value(value: str, allowed: list[str]) -> str:
    # Handle NaN, None, and empty values
    if pd.isna(value) or value is None:
        return ""
    v = str(value).strip()
    if not v:
        return ""
    return v if v in allowed else OTHER_LABEL


def explode_multiselect(series: pd.Series, allowed: list[str]) -> pd.Series:
    # split on commas, trim, bucket unknowns to OTHER_LABEL
    items = []
    for raw in series.dropna().astype(str):
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if not parts:
            continue
        for p in parts:
            items.append(bucket_value(p, allowed))
    return pd.Series([i for i in items if i])


def frequency_for_question(df: pd.DataFrame, col: str) -> pd.DataFrame:
    allowed = ALLOWED.get(col, None)

    if col in MULTI_SELECT:
        if allowed is None:
            # if not specified, just count raw options
            s = explode_multiselect(df[col], allowed=[])
        else:
            s = explode_multiselect(df[col], allowed=allowed)
        counts = s.value_counts(dropna=True)
        total = counts.sum()
        percentages = (counts / total * 100).round(1) if total > 0 else counts * 0
        out = pd.DataFrame({
            "answer": counts.index,
            "count": counts.values,
            "percentage": percentages.values
        })
        return out

    # single-select / free-text
    s = df[col]
    if allowed is not None:
        # Process all non-NaN values - bucket_value handles empty/None cases
        # This ensures "n/a", "0", and other string values are captured
        s = s.apply(lambda v: bucket_value(v, allowed) if pd.notna(v) else "")
        s = s[s != ""]
    else:
        # Convert to string and filter out empty values
        s = s.apply(lambda v: str(v).strip() if pd.notna(v) else "")
        s = s[s != ""]

    counts = s.value_counts(dropna=True)
    total = counts.sum()
    percentages = (counts / total * 100).round(1) if total > 0 else counts * 0
    out = pd.DataFrame({
        "answer": counts.index,
        "count": counts.values,
        "percentage": percentages.values
    })
    return out


def get_all_responses(df: pd.DataFrame, col: str) -> list[str]:
    """Extract all non-empty responses for a question."""
    responses = []
    for value in df[col].dropna():
        if pd.isna(value) or value is None:
            continue
        v = str(value).strip()
        if v:
            responses.append(v)
    return responses


def create_themes_for_frustrations(responses: list[str]) -> dict[str, list[str]]:
    """Group frustration responses into themes based on keywords and patterns."""
    if not responses:
        return {}
    
    # Define theme keywords based on common leadership development frustrations
    themes = {
        "Time constraints": ["time", "busy", "schedule", "hours", "workload", "overwhelmed", "no time", "don't have time", "lack of time"],
        "Lack of feedback/guidance": ["feedback", "guidance", "mentor", "coach", "direction", "advice", "support", "help", "don't know how", "unsure how"],
        "Cost/money": ["cost", "expensive", "money", "price", "afford", "budget", "financial", "pay", "paid"],
        "Not seeing progress/results": ["progress", "results", "improvement", "change", "see results", "measurable", "outcomes", "impact"],
        "Lack of accountability/motivation": ["accountability", "motivation", "discipline", "consistency", "stick with", "follow through", "commitment"],
        "Content not relevant/applicable": ["relevant", "applicable", "practical", "real-world", "useful", "actionable", "relatable"],
        "Information overload/too much": ["overwhelming", "too much", "information overload", "complex", "complicated", "confusing"],
        "Lack of resources/tools": ["resources", "tools", "access", "available", "options", "programs", "platforms"],
        "Organizational/systemic barriers": ["company", "organization", "employer", "system", "culture", "politics", "structure", "management"],
        "Self-doubt/confidence": ["confidence", "self-doubt", "imposter", "worthy", "capable", "qualified", "deserve"],
    }
    
    # Categorize responses
    categorized = {theme: [] for theme in themes.keys()}
    uncategorized = []
    
    for response in responses:
        response_lower = response.lower()
        categorized_flag = False
        
        # Check each theme's keywords
        for theme, keywords in themes.items():
            if any(keyword in response_lower for keyword in keywords):
                categorized[theme].append(response)
                categorized_flag = True
                break
        
        if not categorized_flag:
            uncategorized.append(response)
    
    # Only return themes that have responses
    result = {theme: responses for theme, responses in categorized.items() if responses}
    if uncategorized:
        result["Other/Uncategorized"] = uncategorized
    
    return result


def apply_demographic_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters (Demographics)")
    filtered = df.copy()

    for col in DEMOGRAPHIC_COLS:
        if col not in filtered.columns:
            continue

        allowed = ALLOWED.get(col, None)
        options = sorted([o for o in filtered[col].dropna().unique().astype(str)])
        if allowed:
            # keep the allowed order, append any weird values so user can still filter them
            weird = [o for o in options if o not in allowed]
            options = allowed + sorted(weird)

        selected = st.sidebar.multiselect(col, options=options, default=[])
        if selected:
            filtered = filtered[filtered[col].astype(str).isin(selected)]

    return filtered


# -----------------------------
# App
# -----------------------------
st.set_page_config(page_title="Core15 Survey Results", layout="wide")
st.title("Core15 Survey Results")

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    # Read Excel without converting "n/a" to NaN - preserve all string values
    # keep_default_na=False prevents pandas from auto-converting "n/a", "N/A", etc. to NaN
    df = pd.read_excel(path, keep_default_na=False)
    return df

df = load_data(FILE_PATH)

# Drop Prolific ID from visualization list, but keep it for record count integrity
PROLIFIC_COL = "What is your Prolific ID?"
if PROLIFIC_COL in df.columns:
    df[PROLIFIC_COL] = df[PROLIFIC_COL].astype(str)

filtered = apply_demographic_filters(df)

st.subheader("Sample size")
c1, c2 = st.columns(2)
with c1:
    st.metric("Total responses", len(df))
with c2:
    st.metric("Filtered responses", len(filtered))

st.divider()

# Questions to chart = all columns except Prolific + demographics (demographics are used as filters)
question_cols = [c for c in df.columns if c != PROLIFIC_COL and c not in DEMOGRAPHIC_COLS]

FRUSTRATION_QUESTION = "What frustrates you most about trying to improve as a leader?"

for col in question_cols:
    if col not in filtered.columns:
        continue

    st.markdown(f"### {col}")

    # Special handling for the frustration question
    if col == FRUSTRATION_QUESTION:
        # Get all responses
        all_responses = get_all_responses(filtered, col)
        
        if all_responses:
            # Create themes
            themes = create_themes_for_frustrations(all_responses)
            
            # Display Themes table
            if themes:
                st.markdown("#### Themes")
                theme_data = []
                total_responses = len(all_responses)
                for theme, theme_responses in themes.items():
                    count = len(theme_responses)
                    percentage = round(count / total_responses * 100, 1) if total_responses > 0 else 0
                    theme_data.append({
                        "Theme": theme,
                        "Percentage": percentage
                    })
                themes_df = pd.DataFrame(theme_data)
                st.dataframe(themes_df, use_container_width=True)
            
            # Display all responses
            st.markdown("#### All Responses")
            responses_df = pd.DataFrame({
                "Response": all_responses
            })
            st.dataframe(responses_df, use_container_width=True)
            st.markdown(f"**Total responses: {len(all_responses)}**")
        else:
            st.info("No responses for this question in the filtered set.")
    else:
        # Normal display with bar chart for other questions
        freq = frequency_for_question(filtered, col)

        if freq.empty:
            st.info("No responses for this question in the filtered set.")
            continue

        fig = px.bar(freq, x="answer", y="percentage", custom_data=["count"])
        fig.update_traces(
            hovertemplate="<b>Percentage:</b> %{y}%<br><b>Count:</b> %{customdata[0]}<extra></extra>"
        )
        fig.update_layout(xaxis_title="", yaxis_title="Percentage (%)", bargap=0.2)
        st.plotly_chart(fig, use_container_width=True)