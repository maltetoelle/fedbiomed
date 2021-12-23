import React from 'react';
import {connect, useDispatch} from 'react-redux'
import { getFilesFromRepository } from '../store/actions/repositoryActions';
import RepositoryItem from '../components/RepositoryItem';
import RepositoryBar from '../components/RepositoryBar';
import Button, {ButtonsWrapper} from "../components/Button"
import {useNavigate} from "react-router-dom";
import RepositoryListRow from "../components/RepositoryListRow";
import {ReactComponent as ColumnIcon} from "../assets/img/column-view.svg";
import {ReactComponent as ListIcon} from "../assets/img/list-view.svg";
import { ReactComponent as HomeIcon} from '../assets/img/home.svg';
import { ReactComponent as BackIcon} from "../assets/img/back.svg";

const Repository = (props) => {

    const [selected, setSelected] = React.useState(null)
    const [path] = React.useState(props.path)
    const navigator = useNavigate()
    const dispatch = useDispatch()
    const frameContent = React.useRef(null)
    const mainRepository = React.useRef(null)
    const getFiles = props.getFiles
    const [view, setView] = React.useState(props.view ? props.view : 'list')

    /**
     * Hook for getting files in the repository
     */
    React.useEffect(() => {
        if(path){
            getFiles({path : path}, true)
        }else{
            getFiles({path : []})
        }

    }, [getFiles, path, props.repository.files.length])


    /**
     * Hook for scroll effect when repository width is greater than
     * frame width
     */
    React.useEffect( () => {
        if(mainRepository.current !== null && mainRepository.current.scrollWidth > frameContent.current.offsetWidth ){
            frameContent.current.scrollLeft += mainRepository.current.scrollWidth - frameContent.current.offsetWidth
        }
    })

    const changeView = (view) => {
        setView(view)
    }
    /**
     * Handling click action on single repository
     * item
     * @param {int} indexBar
     * @param {int} index
     * @param {string} type
     * @param {array} path
     */
    const onItemClick = (indexBar, index, type, path) => {

        if(type === "dir") {
            props.getFiles({path: path})
        }

        let indexOld = props.repository.files[indexBar].findIndex( x => x.active === true)

        if(indexOld > -1){
            props.repository.files[indexBar][indexOld].active = false
        }

        props.repository.files[indexBar][index].active = true
        setSelected(props.repository.files[indexBar][index])
    }

    /**
     * When user single click on item in file explorer
     * in list view
     * @param indexBar
     * @param index
     * @param type
     * @param path
     */
    const onListItemClick = (indexBar, index, type, path) => {
        let indexOld = props.repository.files[indexBar].findIndex( x => x.active === true)

        if(indexOld > -1){
            props.repository.files[indexBar][indexOld].active = false
        }
        props.repository.files[indexBar][index].active = true
        setSelected(props.repository.files[indexBar][index])
    }

    /**
     * When list view active and user click on item in breadcrumb
     * @param path
     */
    const onListBreadCrumbClick = (path) => {
        props.getFiles({path: path})
    }

    /**
     * Stop envet propagation when click on add
     * @param {HTMLDomEvent} event
     */
    const onAddActionClick = (event) => {
        event.stopPropagation()
    }

    /**
     * On repository item selected
     * @returns {object}
     */
    const onSelectClick = () => {

        dispatch({type:'NEW_DATASET_TO_ADD' , payload: selected})

        if(props.onSelect){
            props.onSelect(selected)
        }else{
            navigator('/datasets/add-dataset')
        }
        return selected
    }

    const onBackButtonClick = () => {
        let oneBefore = Object.keys(props.repository.folders).at(-2)
        let item = props.repository.folders[oneBefore]

        if(item){
            props.getFiles({path: item.path})
        }
    }
    return (
        <React.Fragment>
            { props.mode === null ? (
                <div className="frame-header">
                    <div style={{margin:'0px 0px'}} className={`header-content`}>
                        <p>Following view displays the datafiles saved in the file system where node runs. To load the datafile, please click on Load Dataset button that comes up when you hover the items in the following list.</p>
                        <div className={'note'}>
                            <div>
                                <div style={{display:'inline-block', marginRight: 10}} className="dot"/>
                                Datasets loaded in the node.
                                <div style={{display:'inline-block', marginRight: 10, marginLeft:10}} className="dot empty"/>
                                Folders that includes dataset loaded in the node
                            </div>
                        </div>
                    </div>
                </div>
            ) : null}
            {
                <div className={"views"}>
                    <div className={"back"}>
                        <div className={"icon"} onClick={onBackButtonClick}>
                            <BackIcon/>
                        </div>
                    </div>
                    <div className={"breadcrumb"}>
                        {Object.keys(props.repository.folders).map((item, key) => {
                               let pathFol = props.repository.folders[item].path
                                return (
                                    <React.Fragment key={key}>
                                        <div className={'item'} onClick={ () => onListBreadCrumbClick(pathFol)}>
                                           {pathFol.length > 0 ? (
                                               pathFol.at(-1)
                                           ) : (
                                              <HomeIcon/>
                                           )
                                           }
                                        </div>
                                        <span className={'seperator'}>
                                            /
                                        </span>
                                    </React.Fragment>
                                )
                            })
                        }
                    </div>
                    <div className={"view-options"}>
                        <div className={`icon ${view === 'bar' ? 'active' : ''}`} onClick={() => changeView('bar')}>
                            <ColumnIcon/>
                        </div>
                        <div className={`icon ${view === 'list' ? 'active' : ''}`} onClick={() => changeView('list')}>
                            <ListIcon/>
                        </div>
                    </div>
                </div>
            }
            <div ref={frameContent} className="frame-content">
                { view === 'bar' ? (
                    <div ref={mainRepository} className="main-repository" style={{height: props.maxHeight ? props.maxHeight : '99%' }}>
                        {Object.keys(props.repository.files).map( (itemBar, key) => {
                            if (itemBar >= props.after ){
                                 return (
                                    <RepositoryBar key={`bat-${key}`} style={{height: props.maxHeight ? props.maxHeight : 'unset' }}>
                                        {props.repository.files[itemBar].map( (item,keyChild) => {

                                            if(props.mode === "file-browser" && item.registered ){
                                                return null
                                            }else{
                                                return (
                                                    <RepositoryItem
                                                        key={`item-${keyChild}`}
                                                        indexBar={itemBar}
                                                        index={keyChild}
                                                        item={item}
                                                        active={item.active}
                                                        onItemClick={onItemClick}
                                                        onAddActionClick={onAddActionClick}
                                                        onItemAddClick={props.onItemAddClick ? props.onItemAddClick : null}
                                                        actionText={props.actionText ? props.actionText : 'Load Dataset'}
                                                        displayAdd={props.mode === "preview" || props.mode === "file-browser" ? false : true}
                                                    />
                                                )
                                            }
                                        })}
                                        {
                                            props.repository.folders[itemBar].displays <  props.repository.folders[itemBar].number ? (
                                                <div className={"end"}>
                                                    Only displaying {props.repository.folders[itemBar].displays} out of {props.repository.folders[itemBar].number}
                                                </div>
                                            ) : null
                                        }
                                    </RepositoryBar>
                                )
                            }else{
                                return null
                            }
                        })}
                    </div>
                    ) : (
                        <div className={'main-repository-list'} style={{height: props.maxHeight ? props.maxHeight : '99%' }} >
                            <div className={'repository-list'}>
                                <table className={'repository-table'}>
                                    <tbody>
                                    <tr>
                                        <th>File/Folder</th>
                                        <th>Size</th>
                                        <th>Created at</th>
                                        <th>Action</th>
                                        <th>State</th>
                                    </tr>
                                        {   props.repository.files[props.repository.level] && props.repository.files[props.repository.level].map((item, key) => {
                                                return(
                                                    <RepositoryListRow
                                                        key={key}
                                                        index={key}
                                                        item={item}
                                                        onItemDoubleClick={onItemClick}
                                                        onItemClick={onListItemClick}
                                                        level={props.repository.level}
                                                        active={item.active}
                                                        displayAdd={props.mode === "preview" || props.mode === "file-browser" ? false : true}
                                                    />
                                                )
                                            })
                                        }
                                    </tbody>
                                </table>
                                {   props.repository.level &&
                                    props.repository.folders[props.repository.level] &&
                                    props.repository.folders[props.repository.level].displays <  props.repository.folders[props.repository.level].number ? (
                                        <div className={"end"}>
                                            Only displaying {props.repository.folders[props.repository.level].displays} out of {props.repository.folders[props.repository.level].number}
                                        </div>
                                    ) : null
                                }
                            </div>
                        </div>
                    )
                }
            </div> 
            <div className="frame-footer">
                { props.mode === "file-browser" ? (
                    <ButtonsWrapper className={"float-right"}>
                    {
                        selected ? (
                            <Button
                                style={{'minWidth' : '100px'}}
                                onClick={onSelectClick}
                            >{
                                selected.type === 'file' ? (
                                    'Select File'
                                ):
                                selected.type === 'dir' ?
                                   'Select Folder'
                                 : null
                            }
                            </Button>
                        ) : null
                    }
                </ButtonsWrapper>
                ) : null}

            </div>
        </React.Fragment>
    );
}

// Default props
Repository.defaultProps = {
    after : 0,
    path  : null,
    mode  : null,
}

// Redux state to props
const mapStateToProps = (state) => {
    return {
        repository : state.repository
    }
}

// Redux dispatch functions to props
const mapDispatchToProps = (dispatch) => {
    return {
        getFiles: (data, fresh) => dispatch(getFilesFromRepository(data, fresh))
    }
}

export default connect(mapStateToProps, mapDispatchToProps)(Repository);