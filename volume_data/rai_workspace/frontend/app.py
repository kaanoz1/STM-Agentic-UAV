
from function_def_run_streamlit_app import run_streamlit_app

def main() -> None: 
    run_streamlit_app(agent=None, page_title="Test Title", initial_message="This is the initial message for testing the streamlit ui.") # type: ignore



if __name__ == "__main__":
    main()