import React from 'react';
import Repository from "../../pages/repository";
import Modal from "./Modal"
import {Label} from "./Inputs";
import Button from "./Button";


const FileBrowser = (props) => {

    const [show, setShow] = React.useState(false)


    /**
     * On folder or file is selected
     * @param {str} selection
     */
    const onSelect = (selection) => {
        props.onSelect(selection)
        setShow(false)
    }


    /**
     * On Modal is closed this method will be triggered
     */
    const onModalClose = () => {
        setShow(false)
    }


    const openRepositoryModal = () => {
        setShow(true)
    }

    return (
        <React.Fragment>
           <div className={`form-control`}>
               {
                   props.label ? (
                        <Label>{props.label}</Label>
                   ) : null
               }
                <div className={"repository-select"}>
                    <Button onClick={openRepositoryModal}>Select Data File</Button>
                    <div className={`path`}>
                        { props.folderPath ?  '/'+ props.folderPath.join('/') : null}
                    </div>
                </div>
            </div>
            <Modal show={show} width="90%" onModalClose={onModalClose}>
                    <Modal.Header>
                        <h1>Select File or Folder</h1>
                    </Modal.Header>
                    <Modal.Content>
                        <Repository
                            onSelect={onSelect}
                            mode={'file-browser'}
                            maxHeight="500px"
                        />
                    </Modal.Content>
            </Modal>
        </React.Fragment>
    );
};

export default FileBrowser;