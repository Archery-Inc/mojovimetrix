/**
 * File: util_widget.js
 * Project: Jovimetrix
 *
 */

const my_map = {
    STRING: "📝",
    BOOLEAN: "🇴",
    INT: "🔟",
    FLOAT: "🛟",
    VEC2: "🇽🇾",
    VEC2INT: "🇽🇾",
    VEC3: "🇽🇾\u200c🇿",
    VEC3INT: "🇽🇾\u200c🇿",
    VEC4: "🇽🇾\u200c🇿\u200c🇼",
    VEC4INT: "🇽🇾\u200c🇿\u200c🇼",
}

export const CONVERTED_TYPE = "converted-widget"
export const CONVERTED_JOV_TYPE = "converted-widget-jovi"

// return the internal mapping type name
export function widget_type_name(type) { return my_map[type];}

export function widget_get_type(config) {
    // Special handling for COMBO so we restrict links based on the entries
    let type = config?.[0]
    let linkType = type
    if (type instanceof Array) {
      type = 'COMBO'
      linkType = linkType.join(',')
    }
    return { type, linkType }
}

export function widget_remove(node, widgetOrSlot) {
    let index = 0;
    if (typeof widgetOrSlot === 'number') {
        index = widgetOrSlot;
    }
    else if (widgetOrSlot) {
        index = node.widgets.indexOf(widgetOrSlot);
    }
    if (index > -1) {
        const w = node.widgets[index];
        if (w.canvas) {
            w.canvas.remove()
        }
        if (w.inputEl) {
            w.inputEl.remove()
        }
        w.onRemoved?.()
        node.widgets.splice(index, 1);
    }
}

export function widget_remove_all(node) {
    if (node.widgets) {
        for (const w of node.widgets) {
            widget_remove(node, w);
        }
        who.widgets.length = 0;
    }
}

export function process_value(input, widget, precision=0, visible=false, typ="number") {
    if (!input) {
        if (visible) {
            widget_show(widget);
            widget.origType = widget.type;
            widget.type = typ;
        }
    }
    widget.options.precision = precision;
    if (precision == 0) {
        widget.options.step = 10;
        widget.options.round = 1;
    } else {
        widget.options.step = 1;
        widget.options.round =  0.1;
    }
}

export function widget_hide(node, widget, suffix = '') {
    if (widget.hidden || widget.type == CONVERTED_TYPE + suffix) {
        return
    }
    widget.origType = widget.type
    widget.hidden = true
    widget.origComputeSize = widget.computeSize
    widget.origSerializeValue = widget.serializeValue
    widget.computeSize = () => [0, -4]
    widget.type = CONVERTED_TYPE + suffix
    widget.serializeValue = () => {
        // Prevent serializing the widget if we have no input linked
        try {
            const { link } = node.inputs.find((i) => i.widget?.name === widget.name)
            if (link == null || link == undefined) {
                return undefined
            }
        } catch(Exception) {

        }
        return widget.origSerializeValue
            ? widget.origSerializeValue()
            : widget.value
    }

    // Hide any linked widgets, e.g. seed+seedControl
    if (widget.linkedWidgets) {
        for (const w of widget.linkedWidgets) {
            widget_hide(node, w, ':' + widget.name)
        }
    }
}

export function widget_show(widget) {
    widget.type = widget.origType
    widget.computeSize = widget.origComputeSize
    widget.computeSize = (target_width) => [target_width, 20]
    widget.serializeValue = widget.origSerializeValue
    delete widget.origType
    delete widget.origComputeSize
    delete widget.origSerializeValue
    widget.hidden = false;

    // Hide any linked widgets, e.g. seed+seedControl
    if (widget.linkedWidgets) {
      for (const w of widget.linkedWidgets) {
        widget_show(w)
      }
    }
}

export function convertToWidget(node, widget) {
    widget_show(widget)
    const sz = node.size
    node.removeInput(node.inputs.findIndex((i) => i.widget?.name === widget.name))

    for (const widget of node.widgets) {
      widget.last_y -= LiteGraph.NODE_SLOT_HEIGHT
    }

    // Restore original size but grow if needed
    node.setSize([Math.max(sz[0], node.size[0]), Math.max(sz[1], node.size[1])])
}

export function convertToInput(node, widget, config) {
    // console.log(node, widget)
    widget_hide(node, widget)

    const { linkType } = widget_get_type(config)

    // Add input and store widget config for creating on primitive node
    const sz = node.size
    node.addInput(widget.name, linkType, {
      widget: { name: widget.name, config },
    })

    for (const widget of node.widgets) {
      widget.last_y += LiteGraph.NODE_SLOT_HEIGHT
    }

    // Restore original size but grow if needed
    node.setSize([Math.max(sz[0], node.size[0]), Math.max(sz[1], node.size[1])])
}
