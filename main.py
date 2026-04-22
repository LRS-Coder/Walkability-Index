# import local modules
from download import download_confirm
from transform import select_subfolder, run_transform
from visualise import run_visualise

# main menu where user selects which modules to run
while True:
    # user is prompted to answer with either 1, 2, 3, 4, or exit
    print('Main Menu\n1: Run Full Pipeline\n2: Download Data Only\n3: Transform Data Only\n4: Visualise Data Only')
    choice = input("Please select 1-4 or enter 'exit': ").strip().lower()

    # run full pipeline using modules from download, transform, and visualise
    if choice == '1':
        subfolder = download_confirm()

        # pass subfolder createc with download_confirm into transform and visualise
        if subfolder:
            run_transform(subfolder)
            run_visualise(subfolder)

    # only run the download module
    elif choice == '2':
        download_confirm()

    # user selects a subfolder and the run_transform module is applied to its data
    elif choice == '3':
        subfolder = select_subfolder()
        run_transform(subfolder)

    # user selects a subfolder and the data is visualised using the run_visualise module
    elif choice == '4':
        subfolder = select_subfolder()
        run_visualise(subfolder)

    # uaer exits the main menu and the program ends
    elif choice in ['e', 'exit']:
        print('Exiting...')
        break

    # if user inputs a value that is not 1, 2, 3, 4, e, or exit they are reminded of the valid inputs and user will try again
    else:
        print("Please select a number between 1 and 4 or enter 'exit'")