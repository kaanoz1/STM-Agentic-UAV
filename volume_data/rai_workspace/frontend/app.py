
from function_def_run_streamlit_app import run_streamlit_app
from rai_workspace.agent.function_def_initialize_agent import initialize_agent
def main() -> None: 
    run_streamlit_app(agent=initialize_agent(), 
                      page_title="Test Title", 
                      initial_message="This is the initial message for testing the streamlit ui.") # type: ignore



if __name__ == "__main__":
    main()