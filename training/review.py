import streamlit.config as st_config
from review.cli import setup_argparse
from review.config import AppConfig
from review.ui.app import JSONReviewApp


def main():
    parser = setup_argparse()
    args = parser.parse_args()

    config = AppConfig.from_args(args)
    app = JSONReviewApp(config)

    # Configure Streamlit server
    st_config.set_option("server.port", args.port)

    app.run()


if __name__ == "__main__":
    main()
