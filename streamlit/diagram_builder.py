import base64

import streamlit as st
import streamlit.components.v1 as components
from aiweb_common.streamlit.streamlit_common import apply_uab_font, hide_streamlit_branding
from Api import (
    ENDPOINT_MAP,
    MODE_LABELS,
    UML_DIAGRAM_TYPES,
    build_prompt_description,
    generate_diagram,
    render_diagram,
)

THEME_OPTIONS = [
    ("", "Default PlantUML styling"),
    ("plain", "Minimal, neutral styling"),
    ("lightgray", "Soft light gray palette"),
    ("blueprint", "White on blue blueprint look"),
    ("cerulean", "Bright Bootstrap cerulean palette"),
    ("cerulean-outline", "Cerulean with stronger outlines"),
    ("materia", "Material-inspired modern styling"),
    ("materia-outline", "Material styling with stronger outlines"),
    ("minty", "Fresh green Bootstrap-style palette"),
    ("sandstone", "Warm sandstone Bootstrap palette"),
    ("spacelab", "Cool blue-gray Bootstrap palette"),
    ("superhero", "Dark high-contrast Bootstrap palette"),
    ("united", "Warm orange Bootstrap palette"),
    ("cyborg", "Dark cyborg theme"),
    ("cyborg-outline", "Dark cyborg theme with stronger outlines"),
    ("carbon-gray", "Gray Carbon design system palette"),
    ("cloudscape-design", "AWS Cloudscape design palette"),
    ("aws-orange", "AWS-inspired orange accent palette"),
    ("silver", "Muted silver palette"),
    ("mars", "Reddish Mars-inspired palette"),
    ("reddress", "Bold red-accented styling"),
    ("vibrant", "High-saturation colorful palette"),
    ("toy", "Playful colorful styling"),
    ("mono", "Monochrome black-and-white"),
    ("sketchy", "Hand-drawn sketch look"),
    ("sketchy-outline", "Sketch look with stronger outlines"),
    ("hacker", "Terminal-inspired hacker theme"),
    ("crt-green", "Green CRT monitor look"),
    ("crt-amber", "Amber CRT monitor look"),
    ("metal", "Metallic styling"),
    ("mimeograph", "Purple on gray vintage print look"),
    ("amiga", "Retro Amiga Workbench look"),
]

FRIENDLY_MODE_LABELS = {
    "uml": "Diagrams",
    "mindmap": "Mind maps",
    "ui_mockup": "Screen mockups",
    "gantt": "Project timelines",
    "erd": "Data maps",
    "json": "Structured data views",
    "c4": "System overviews",
}

FRIENDLY_MODE_HELP = {
    "uml": "Turn an idea, process, or workflow into a diagram (UML diagram).",
    "mindmap": "Organize ideas into a visual map (mind map).",
    "ui_mockup": "Sketch a simple app or webpage layout (UI mockup / SALT).",
    "gantt": "Lay out a project plan over time (Gantt chart).",
    "erd": "Map out data tables and how they connect (entity-relationship diagram).",
    "json": "Visualize structured information clearly (JSON diagram).",
    "c4": "Show how parts of a system fit together (C4 diagram).",
}

UML_TYPE_LABELS = {
    "Use Case": "People and actions (Use Case)",
    "Class": "Objects and relationships (Class)",
    "Activity": "Step-by-step process (Activity)",
    "Component": "System parts (Component)",
    "Deployment": "Where things run (Deployment)",
    "State Machine": "Changes over time (State Machine)",
    "Timing": "Timing and sequence (Timing)",
    "Sequence": "Back-and-forth interactions (Sequence)",
}


def _state_key(mode: str, field: str) -> str:
    return f"{field}_{mode}"


def _init_session_state() -> None:
    for mode in MODE_LABELS:
        defaults = {
            "chat_history": [],
            "plantuml_code": "",
            "image_base64": None,
            "status_message": "",
            "error_message": "",
        }
        for field, default in defaults.items():
            key = _state_key(mode, field)
            if key not in st.session_state:
                st.session_state[key] = default
        draft_key = _state_key(mode, "draft_request")
        if draft_key not in st.session_state:
            st.session_state[draft_key] = ""
        submit_key = _state_key(mode, "submit_request")
        if submit_key not in st.session_state:
            st.session_state[submit_key] = False

    if "theme" not in st.session_state:
        st.session_state["theme"] = ""
    if "theme_index" not in st.session_state:
        st.session_state["theme_index"] = 0
    if "uml_subtype" not in st.session_state:
        st.session_state["uml_subtype"] = "Use Case"


def _handle_chat_input(mode: str, user_message: str) -> None:
    history_key = _state_key(mode, "chat_history")
    code_key = _state_key(mode, "plantuml_code")
    img_key = _state_key(mode, "image_base64")
    status_key = _state_key(mode, "status_message")
    error_key = _state_key(mode, "error_message")

    history = st.session_state[history_key]
    history.append({"role": "user", "content": user_message})

    current_code = st.session_state.get(code_key, "")
    diagram_type = st.session_state.get("uml_subtype", "Use Case") if mode == "uml" else ENDPOINT_MAP[mode][2]
    description = build_prompt_description(
        user_request=user_message,
        current_code=current_code,
        chat_history=history,
        mode=mode,
        diagram_type=diagram_type,
    )

    with st.spinner("Generating diagram..."):
        result, error = generate_diagram(
            mode=mode,
            description=description,
            diagram_type=diagram_type,
            theme=st.session_state.get("theme") or None,
        )

    if error:
        st.session_state[error_key] = error
        st.session_state[status_key] = ""
        history.append({"role": "assistant", "content": f"Error: {error}"})
    elif result and result.get("status") == "ok":
        st.session_state[code_key] = result.get("plantuml_code", current_code)
        # A keyed text_area ignores later ``value=`` changes, so write the new
        # code into the editor's own state for it to show up.
        st.session_state[_state_key(mode, "code_editor")] = st.session_state[code_key]
        st.session_state[img_key] = result.get("image_base64")
        message = result.get("message", "Diagram generated.")
        st.session_state[status_key] = message
        st.session_state[error_key] = ""
        history.append({"role": "assistant", "content": message})
    else:
        message = (result or {}).get("message", "Generation failed.")
        st.session_state[error_key] = message
        st.session_state[status_key] = ""
        history.append({"role": "assistant", "content": f"Error: {message}"})

    st.session_state[history_key] = history


def _handle_rerender(mode: str) -> None:
    code_key = _state_key(mode, "plantuml_code")
    img_key = _state_key(mode, "image_base64")
    status_key = _state_key(mode, "status_message")
    error_key = _state_key(mode, "error_message")

    # Read the editor itself: in a button callback the synced copy may lag the edit.
    code = st.session_state.get(_state_key(mode, "code_editor"), st.session_state.get(code_key, ""))
    st.session_state[code_key] = code
    if not code.strip():
        st.session_state[error_key] = "No PlantUML code to render."
        st.session_state[status_key] = ""
        return

    with st.spinner("Rendering diagram..."):
        result, error = render_diagram(mode=mode, plantuml_code=code)

    if error:
        st.session_state[error_key] = error
        st.session_state[status_key] = ""
    elif result and result.get("status") == "ok" and result.get("image_base64"):
        rendered_code = result.get("plantuml_code") or ""
        if rendered_code and rendered_code != code:
            st.session_state[code_key] = rendered_code
            st.session_state[_state_key(mode, "code_editor")] = rendered_code
        st.session_state[img_key] = result.get("image_base64")
        # The server message already includes any plan-check warnings.
        st.session_state[status_key] = result.get("message", "Rendered successfully.")
        st.session_state[error_key] = ""
    else:
        st.session_state[error_key] = (result or {}).get("message", "Rendering failed.")
        st.session_state[status_key] = ""


def _pan_zoom_image(img_b64: str, height: int = 500) -> None:
    html = f"""
    <style>
        #pz-container {{
            width: 100%; height: {height}px; overflow: hidden;
            border: 1px solid #444; border-radius: 6px; position: relative;
            cursor: grab; background: #1a1a2e; touch-action: none;
        }}
        #pz-container:fullscreen {{ height: 100vh; border: none; border-radius: 0; }}
        #pz-container.grabbing {{ cursor: grabbing; }}
        #pz-img {{ position: absolute; top: 0; left: 0; transform-origin: 0 0; user-select: none; -webkit-user-drag: none; }}
        #pz-controls {{ position: absolute; top: 8px; right: 8px; display: flex; gap: 4px; z-index: 10; pointer-events: none; }}
        #pz-controls button, #pz-controls span {{ pointer-events: auto; }}
        #pz-controls button {{ width: 32px; height: 32px; border: 1px solid #555; border-radius: 4px; background: rgba(30,30,46,0.85); color: #ccc; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; line-height: 1; }}
        #pz-controls button:hover {{ background: rgba(60,60,80,0.95); color: #fff; }}
        #pz-zoom-level {{ font-size: 12px; color: #bbb; background: rgba(30,30,46,0.85); border: 1px solid #666; border-radius: 4px; padding: 4px 8px; display: flex; align-items: center; }}
    </style>
    <div id="pz-container">
        <div id="pz-controls">
            <button id="pz-fs" title="Full screen">&#x26F6;</button>
            <button id="pz-in" title="Zoom in">+</button>
            <button id="pz-out" title="Zoom out">&minus;</button>
            <button id="pz-fit" title="Fit to view">&#x2922;</button>
            <button id="pz-reset" title="Reset (actual size)">1:1</button>
            <span id="pz-zoom-level">100%</span>
        </div>
        <img id="pz-img" src="data:image/png;base64,{img_b64}" draggable="false" />
    </div>
    <script>
    (function() {{
        const c=document.getElementById('pz-container'),img=document.getElementById('pz-img'),zl=document.getElementById('pz-zoom-level');
        let s=1,px=0,py=0,dr=false,sx=0,sy=0,spx=0,spy=0;
        function ap(){{img.style.transform='translate('+px+'px,'+py+'px) scale('+s+')';zl.textContent=Math.round(s*100)+'%';}}
        function fit(){{const cw=c.clientWidth,ch=c.clientHeight,iw=img.naturalWidth,ih=img.naturalHeight;if(!iw||!ih)return;s=Math.min(cw/iw,ch/ih,1);px=(cw-iw*s)/2;py=(ch-ih*s)/2;ap();}}
        img.onload=fit;if(img.complete&&img.naturalWidth)fit();
        c.addEventListener('wheel',function(e){{e.preventDefault();const r=c.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,f=e.deltaY<0?1.15:1/1.15,ns=Math.min(Math.max(s*f,0.1),10);px=mx-(mx-px)*(ns/s);py=my-(my-py)*(ns/s);s=ns;ap();}},{{passive:false}});
        c.addEventListener('pointerdown',function(e){{if(e.button!==0||e.target.closest('#pz-controls'))return;dr=true;sx=e.clientX;sy=e.clientY;spx=px;spy=py;c.classList.add('grabbing');c.setPointerCapture(e.pointerId);}});
        c.addEventListener('pointermove',function(e){{if(!dr)return;px=spx+(e.clientX-sx);py=spy+(e.clientY-sy);ap();}});
        c.addEventListener('pointerup',function(){{dr=false;c.classList.remove('grabbing');}});
        c.addEventListener('dblclick',function(e){{if(e.target.closest('#pz-controls'))return;fit();}});
        document.getElementById('pz-fs').addEventListener('click',function(){{var t=window.frameElement||c;t.requestFullscreen().then(function(){{c.style.height='100vh';c.style.width='100vw';setTimeout(fit,100);}}).catch(function(){{}});}});
        document.getElementById('pz-in').addEventListener('click',function(){{const r=c.getBoundingClientRect(),cx=r.width/2,cy=r.height/2,ns=Math.min(s*1.3,10);px=cx-(cx-px)*(ns/s);py=cy-(cy-py)*(ns/s);s=ns;ap();}});
        document.getElementById('pz-out').addEventListener('click',function(){{const r=c.getBoundingClientRect(),cx=r.width/2,cy=r.height/2,ns=Math.max(s/1.3,0.1);px=cx-(cx-px)*(ns/s);py=cy-(cy-py)*(ns/s);s=ns;ap();}});
        document.getElementById('pz-fit').addEventListener('click',fit);
        document.getElementById('pz-reset').addEventListener('click',function(){{s=1;const cw=c.clientWidth,ch=c.clientHeight,iw=img.naturalWidth,ih=img.naturalHeight;px=(cw-iw)/2;py=(ch-ih)/2;ap();}});
    }})();
    </script>
    """
    components.html(html, height=height + 4, scrolling=False)


def _render_mode_tab(mode: str) -> None:
    history_key = _state_key(mode, "chat_history")
    code_key = _state_key(mode, "plantuml_code")
    img_key = _state_key(mode, "image_base64")
    status_key = _state_key(mode, "status_message")
    error_key = _state_key(mode, "error_message")

    st.markdown(FRIENDLY_MODE_HELP[mode])

    if mode == "uml":
        settings_col1, settings_col2 = st.columns(2)
        with settings_col1:
            current_subtype = st.session_state.get("uml_subtype", "Use Case")
            idx = UML_DIAGRAM_TYPES.index(current_subtype) if current_subtype in UML_DIAGRAM_TYPES else 0
            st.session_state["uml_subtype"] = st.selectbox(
                "What kind of diagram would you like to make?",
                options=UML_DIAGRAM_TYPES,
                index=idx,
                format_func=lambda value: UML_TYPE_LABELS.get(value, value),
                key=f"uml_subtype_select_{mode}",
            )
        theme_container = settings_col2
    else:
        theme_container = st.container()

    current_theme = st.session_state.get("theme", "")
    current_theme_index = next(
        (i for i, (theme_name, _) in enumerate(THEME_OPTIONS) if theme_name == current_theme),
        0,
    )
    with theme_container:
        selected_theme = st.selectbox(
            "Choose a visual style",
            options=range(len(THEME_OPTIONS)),
            index=current_theme_index,
            format_func=lambda i: "Default" if THEME_OPTIONS[i][0] == "" else THEME_OPTIONS[i][0],
            key=f"theme_select_{mode}",
        )
        st.session_state["theme"] = THEME_OPTIONS[selected_theme][0]
        st.caption(THEME_OPTIONS[selected_theme][1])

    history = st.session_state.get(history_key, [])
    draft_key = _state_key(mode, "draft_request")
    submit_key = _state_key(mode, "submit_request")

    if st.session_state.get(submit_key):
        pending_input = st.session_state.get(draft_key, "").strip()
        st.session_state[submit_key] = False
        if pending_input:
            _handle_chat_input(mode, pending_input)
            st.session_state[draft_key] = ""
            st.rerun()

    user_input = st.text_area(
        "Describe what you want to create (or change)",
        placeholder="For example: Create a simple workflow for a patient check-in process, or revise the current diagram to add a review step.",
        height=180,
        key=draft_key,
    )
    _, submit_center, _ = st.columns([1.5, 1, 1.5])
    with submit_center:
        if st.button("Create", key=f"generate_{mode}", type="primary", use_container_width=True):
            if user_input.strip():
                st.session_state[submit_key] = True
                st.rerun()

    if history:
        with st.expander("Previous requests", expanded=False):
            for msg in history:
                with st.chat_message("user" if msg.get("role") == "user" else "assistant"):
                    st.markdown(msg.get("content", ""))

    img_b64 = st.session_state.get(img_key)
    if img_b64:
        _pan_zoom_image(img_b64, height=550)
        preview_col1, preview_col2 = st.columns([3, 1])
        with preview_col1:
            st.caption(
                "Scroll to zoom, drag to pan, double-click to fit. "
                "Revise by entering changes above and clicking Create."
            )
        with preview_col2:
            st.download_button(
                label="Download image (PNG)",
                data=base64.b64decode(img_b64),
                file_name=f"{mode}_diagram.png",
                mime="image/png",
                key=f"dl_image_{mode}",
                use_container_width=True,
            )
    else:
        st.info("Your diagram preview will appear here after you create it.")

    with st.expander("Diagram code", expanded=False):
        new_code = st.text_area(
            "Edit diagram text",
            height=300,
            key=_state_key(mode, "code_editor"),
            label_visibility="collapsed",
        )
        if new_code != st.session_state.get(code_key, ""):
            st.session_state[code_key] = new_code

        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            # on_click runs before the page is redrawn, so the handler may update the
            # editor widget's state (it cannot once the text area exists).
            st.button(
                "Refresh preview", key=f"rerender_{mode}", on_click=_handle_rerender, args=(mode,)
            )
        with btn_col2:
            code = st.session_state.get(code_key, "")
            if code:
                st.download_button(
                    label="Download diagram text",
                    data=code,
                    file_name=f"{mode}_diagram.puml",
                    mime="text/plain",
                    key=f"dl_code_{mode}",
                )
        with btn_col3:
            if st.button("Clear requests", key=f"clear_history_{mode}"):
                st.session_state[history_key] = []
                st.session_state[status_key] = ""
                st.session_state[error_key] = ""
                st.rerun()

    error_msg = st.session_state.get(error_key, "")
    status_msg = st.session_state.get(status_key, "")
    if error_msg:
        st.error(error_msg)
    elif status_msg:
        st.success(status_msg)


def show_diagram_page() -> None:
    st.set_page_config(page_title="Diagram Builder", page_icon="\U0001f4d0", layout="wide")
    hide_streamlit_branding()
    apply_uab_font()

    st.title("\U0001f4d0 Diagram Builder")
    st.markdown(
        "Describe an idea, process, or system in everyday language and get a visual diagram you can refine and download."
    )
    st.markdown("---")

    _init_session_state()

    tabs = st.tabs(list(FRIENDLY_MODE_LABELS.values()))
    for tab, mode in zip(tabs, FRIENDLY_MODE_LABELS):
        with tab:
            _render_mode_tab(mode)


if __name__ == "__main__":
    show_diagram_page()
