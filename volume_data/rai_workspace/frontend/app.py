
from rai_workspace.frontend.function_def_run_streamlit_app import run_streamlit_app
from rai_workspace.agent.function_def_initialize_agent import initialize_agent


def main() -> None: 
    run_streamlit_app(agent=initialize_agent(), 
                      page_title="İHA Kontrol Paneli", 
                      initial_message="Merhaba.") # type: ignore



if __name__ == "__main__":
    main()