import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: win
    width: 1240; height: 840
    minimumWidth: 1040; minimumHeight: 740
    visible: true
    title: "Brother Studio"
    color: bg
    property color bg: studio.theme.background
    property color surface: studio.theme.surface
    property color fg: studio.theme.foreground
    property color muted: studio.theme.muted
    property color accent: studio.theme.accent
    property color green: studio.theme.green
    property color red: studio.theme.red
    property color edge: Qt.alpha(fg, 0.12)
    property int section: 0
    property int selectedPage: 0
    property bool closingConfirmed: false
    property bool reducedMotion: false
    onSectionChanged: pageTransition.restart()
    readonly property var currentPage: studio.pages.length > 0 ? studio.pages[Math.min(selectedPage, studio.pages.length - 1)] : null
    font.family: "Inter"
    font.pixelSize: 14
    palette.window: bg
    palette.windowText: fg
    palette.base: surface
    palette.text: fg
    palette.button: surface
    palette.buttonText: fg
    palette.highlight: accent
    palette.highlightedText: fg
    palette.placeholderText: muted
    palette.alternateBase: bg
    palette.light: surface
    palette.midlight: surface
    palette.mid: edge
    palette.dark: bg
    palette.shadow: bg
    palette.brightText: fg
    palette.toolTipBase: surface
    palette.toolTipText: fg
    palette.link: accent
    palette.linkVisited: accent
    palette.accent: accent
    NumberAnimation { id: pageTransition; target: workspace; property: "opacity"; from: 0.25; to: 1; duration: win.reducedMotion ? 0 : 220; easing.type: Easing.OutCubic }
    onClosing: function(close) {
        if (!closingConfirmed && (studio.busy || studio.pages.length > 0)) {
            close.accepted = false
            closeDialog.open()
        }
    }

    component Caption: Label {
        color: win.muted
        font.pixelSize: 11
        font.weight: Font.DemiBold
        font.letterSpacing: 1.4
    }
    component Action: Button {
        id: action
        property bool primary: false
        property bool danger: false
        implicitHeight: 42
        implicitWidth: Math.max(90, contentItem.implicitWidth + 32)
        hoverEnabled: true
        font.weight: Font.DemiBold
        contentItem: Text {
            text: action.text
            color: !action.enabled ? win.muted : action.primary ? win.bg : action.danger ? win.red : win.fg
            font: action.font
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            opacity: action.enabled ? 1 : 0.45
        }
        background: Rectangle {
            radius: 9
            color: action.primary ? win.accent : action.hovered ? Qt.alpha(win.fg, 0.09) : Qt.alpha(win.fg, 0.035)
            opacity: action.enabled ? 1 : 0.35
            border.color: action.activeFocus ? win.accent : action.primary ? "transparent" : win.edge
            border.width: action.activeFocus ? 2 : 1
            Behavior on color { ColorAnimation { duration: win.reducedMotion ? 0 : 130 } }
            scale: action.down ? 0.97 : 1
            Behavior on scale { NumberAnimation { duration: win.reducedMotion ? 0 : 120 } }
        }
    }
    component Field: ComboBox {
        id: field
        implicitHeight: 42
        Layout.fillWidth: true
        font.pixelSize: 14
        background: Rectangle {
            color: Qt.alpha(win.fg, 0.035); radius: 8
            border.color: field.activeFocus ? win.accent : win.edge
        }
        contentItem: Text {
            text: field.displayText; color: field.enabled ? win.fg : win.muted
            leftPadding: 14; rightPadding: 30
            verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
            font: field.font
        }
        indicator: Text {
            x: field.width - width - 14; anchors.verticalCenter: parent.verticalCenter
            text: "⌄"; color: win.muted; font.pixelSize: 20
        }
        delegate: ItemDelegate {
            required property var modelData
            width: field.width
            text: modelData
            highlighted: field.highlightedIndex === index
            contentItem: Text { text: parent.text; color: win.fg; font: field.font }
            background: Rectangle { color: parent.highlighted ? Qt.alpha(win.accent, 0.18) : win.surface; radius: 4 }
        }
        popup: Popup {
            y: field.height + 4; width: field.width
            implicitHeight: Math.min(contentItem.implicitHeight + 12, 260)
            padding: 6
            contentItem: ListView {
                clip: true; implicitHeight: contentHeight
                model: field.popup.visible ? field.delegateModel : null
                currentIndex: field.highlightedIndex
            }
            background: Rectangle { color: win.surface; border.color: win.edge; radius: 10 }
        }
    }
    component TextInput: TextField {
        implicitHeight: 42
        color: win.fg; selectionColor: win.accent; selectedTextColor: win.bg
        placeholderTextColor: win.muted
        leftPadding: 14; rightPadding: 14
        background: Rectangle {
            color: Qt.alpha(win.fg, 0.035); radius: 8
            border.color: parent.activeFocus ? win.accent : win.edge
        }
    }
    component Panel: Rectangle {
        radius: 14; color: Qt.alpha(win.fg, 0.025); border.color: win.edge
    }

    FileDialog {
        id: exportDialog
        objectName: "exportDialog"
        options: FileDialog.DontUseNativeDialog
        title: "Save your document"
        fileMode: FileDialog.SaveFile
        nameFilters: ["PDF document (*.pdf)", "PNG image (*.png)", "JPEG image (*.jpg)"]
        defaultSuffix: selectedNameFilter.index === 0 ? "pdf" : selectedNameFilter.index === 1 ? "png" : "jpg"
        onAccepted: studio.export(selectedFile, win.selectedPage)
    }
    FileDialog {
        id: importDialog
        objectName: "importDialog"
        options: FileDialog.DontUseNativeDialog
        title: "Add an image to your document"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)"]
        onAccepted: studio.importImage(selectedFile)
    }
    FileDialog {
        id: printDialog
        objectName: "printDialog"
        options: FileDialog.DontUseNativeDialog
        title: "Choose a file to print"
        nameFilters: ["Printable documents (*.pdf *.png *.jpg *.jpeg *.txt *.ps)", "All files (*)"]
        onAccepted: studio.choosePrintFile(selectedFile)
    }
    Dialog {
        id: closeDialog
        anchors.centerIn: parent
        modal: true; width: 460
        title: "Close Brother Studio?"
        contentItem: Label {
            text: studio.busy ? "An operation is still running. Closing will stop scanning and discard unexported pages." : "Unexported pages will be discarded. Save your document before closing if you need to keep it."
            wrapMode: Text.WordWrap; color: win.fg
        }
        standardButtons: Dialog.Cancel | Dialog.Discard
        onDiscarded: { win.closingConfirmed = true; win.close() }
    }
    Dialog {
        id: clearDialog
        anchors.centerIn: parent; modal: true; width: 410
        title: "Start a new document?"
        contentItem: Label { text: "Current pages will be removed from the workspace. Export them first if you want to keep them."; wrapMode: Text.WordWrap; color: win.fg }
        standardButtons: Dialog.Cancel | Dialog.Discard
        onDiscarded: { studio.clearPages(); win.selectedPage = 0 }
    }
    Dialog {
        id: setupDialog
        anchors.centerIn: parent; modal: true; width: 460
        title: "Add your Brother printer"
        contentItem: Label {
            text: "This enables the CUPS printing service and creates a driverless Brother_MFC_L2800DW queue at " + studio.ip + ". Your desktop may ask for administrator authentication."
            wrapMode: Text.WordWrap; color: win.fg
        }
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: studio.setupPrinter()
    }
    Shortcut { sequence: "Ctrl+S"; enabled: !studio.busy && studio.pages.length > 0; onActivated: exportDialog.open() }
    Shortcut { sequence: "Ctrl+O"; enabled: !studio.busy; onActivated: importDialog.open() }
    Shortcut { sequence: "Escape"; enabled: studio.operation.indexOf("Scanning") === 0; onActivated: studio.cancelScan() }

    RowLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.preferredWidth: 208; Layout.fillHeight: true
            color: Qt.alpha(win.fg, 0.025)
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: win.edge }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 22; spacing: 8
                RowLayout {
                    Layout.topMargin: 8; spacing: 10
                    Image { source: "../../assets/brother-studio.svg"; Layout.preferredWidth: 34; Layout.preferredHeight: 34 }
                    ColumnLayout {
                        spacing: 0
                        Label { text: "brother"; font.pixelSize: 22; font.weight: Font.Bold; color: win.fg; font.letterSpacing: -0.8 }
                        Caption { text: "STUDIO"; font.pixelSize: 9; font.letterSpacing: 3 }
                    }
                }
                Caption { text: "WORKSPACE"; Layout.topMargin: 38; Layout.bottomMargin: 10 }
                Repeater {
                    model: [{label: "Scan", symbol: "▣"}, {label: "Print", symbol: "▤"}, {label: "Documents", symbol: "▥"}, {label: "Device", symbol: "⚙"}]
                    delegate: Button {
                        id: nav
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true; implicitHeight: 46
                        hoverEnabled: true
                        contentItem: RowLayout {
                            spacing: 14
                            Label { text: nav.modelData.symbol; color: win.section === nav.index ? win.accent : win.muted; font.pixelSize: 21; Layout.preferredWidth: 22 }
                            Label { text: nav.modelData.label; color: win.section === nav.index ? win.fg : win.muted; font.weight: win.section === nav.index ? Font.DemiBold : Font.Normal; Layout.fillWidth: true }
                            Rectangle { width: 5; height: 5; radius: 3; color: win.accent; visible: win.section === nav.index }
                        }
                        background: Rectangle {
                            radius: 9
                            color: win.section === nav.index ? Qt.alpha(win.accent, 0.12) : nav.hovered ? Qt.alpha(win.fg, 0.04) : "transparent"
                            border.color: nav.activeFocus ? win.accent : "transparent"
                            Behavior on color { ColorAnimation { duration: win.reducedMotion ? 0 : 180 } }
                        }
                        onClicked: win.section = index
                    }
                }
                Item { Layout.fillHeight: true }
                Panel {
                    Layout.fillWidth: true; implicitHeight: 105
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 7
                        RowLayout {
                            Rectangle { width: 6; height: 6; radius: 3; color: studio.online ? win.green : win.muted }
                            Caption { text: studio.online ? "CONNECTED" : "NOT CONNECTED"; font.pixelSize: 9; font.letterSpacing: 0.7 }
                        }
                        Label { text: "MFC-L2800DW"; font.pixelSize: 13; font.weight: Font.DemiBold; color: win.fg }
                        Label { text: studio.ip; color: win.muted; font.family: "JetBrains Mono"; font.pixelSize: 11 }
                    }
                }
                RowLayout {
                    Layout.topMargin: 14; spacing: 8
                    Rectangle { width: 11; height: 11; radius: 4; color: win.accent }
                    Label { text: studio.theme.themeName; color: win.muted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                }
                Caption { text: "FOLLOWS OMARCHY"; font.pixelSize: 8; font.letterSpacing: 1; Layout.bottomMargin: 5 }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            Item {
                Layout.fillWidth: true; Layout.preferredHeight: 96
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 32; anchors.rightMargin: 32; spacing: 20
                    ColumnLayout {
                        spacing: 5
                        Caption { text: ["CAPTURE / CREATE", "PAPER / OUTPUT", "SAVED / LOCAL", "HARDWARE / NETWORK"][win.section] }
                        Label { text: ["Scan a document", "Print something", "Your documents", "Your Brother"][win.section]; color: win.fg; font.pixelSize: 27; font.weight: Font.DemiBold; font.letterSpacing: -0.7 }
                    }
                    Item { Layout.fillWidth: true }
                    Action { text: "Device settings ↗"; enabled: !studio.busy; onClicked: studio.openDevice() }
                }
                Rectangle { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; anchors.leftMargin: 32; anchors.rightMargin: 32; height: 1; color: win.edge }
            }

            StackLayout {
                id: workspace
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.margins: 28; Layout.topMargin: 24; Layout.bottomMargin: 18
                currentIndex: win.section

                // SCAN
                RowLayout {
                    spacing: 22
                    ColumnLayout {
                        Layout.preferredWidth: 246; Layout.maximumWidth: 246; Layout.fillHeight: true
                        spacing: 9
                        Caption { text: "SCAN SETTINGS"; Layout.bottomMargin: 8 }
                        Label { text: "Source"; color: win.muted; font.pixelSize: 12 }
                        Field { id: scanSource; objectName: "scanSource"; model: studio.sources; enabled: !studio.busy }
                        Label { text: "Colour mode"; color: win.muted; font.pixelSize: 12; Layout.topMargin: 8 }
                        Field {
                            id: scanMode; objectName: "scanMode"; model: studio.modes; enabled: !studio.busy
                            displayText: currentText === "Gray" ? "Grayscale" : currentText === "Color" ? "Colour" : currentText
                        }
                        RowLayout {
                            Layout.topMargin: 8
                            Label { text: "Resolution"; color: win.muted; font.pixelSize: 12 }
                            Item { Layout.fillWidth: true }
                            Label { text: "DPI"; color: win.muted; font.pixelSize: 10 }
                        }
                        Field { id: scanDpi; objectName: "scanResolution"; model: studio.resolutions; currentIndex: Math.max(0, studio.resolutions.indexOf("300")); enabled: !studio.busy }
                        Label { text: "Page size"; color: win.muted; font.pixelSize: 12; Layout.topMargin: 8 }
                        Field { id: scanSize; model: ["A4", "Letter", "Maximum"]; enabled: !studio.busy }
                        Button {
                            id: adjustments
                            text: checked ? "−  Image adjustments" : "+  Image adjustments"
                            checkable: true; flat: true
                            Layout.fillWidth: true; Layout.topMargin: 6
                            contentItem: Label { text: adjustments.text; color: win.muted; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter }
                        }
                        ColumnLayout {
                            visible: adjustments.checked; spacing: 3; Layout.fillWidth: true
                            Label { text: "Brightness  " + Math.round(brightness.value); color: win.muted; font.pixelSize: 11 }
                            Slider { id: brightness; from: -100; to: 100; value: 0; stepSize: 1; Layout.fillWidth: true; enabled: !studio.busy }
                            Label { text: "Contrast  " + Math.round(contrast.value); color: win.muted; font.pixelSize: 11 }
                            Slider { id: contrast; from: -100; to: 100; value: 0; stepSize: 1; Layout.fillWidth: true; enabled: !studio.busy }
                        }
                        Item { Layout.fillHeight: true }
                        Label {
                            text: scanSource.currentText === "ADF" ? "Load pages face up in the feeder.\nOne side per pass." : "Place your document face down\non the scanner glass."
                            wrapMode: Text.WordWrap; color: win.muted; font.pixelSize: 12; lineHeight: 1.4; Layout.fillWidth: true
                        }
                        Action {
                            objectName: "startScan"
                            text: studio.operation.indexOf("Scanning") === 0 ? "Stop scanning" : studio.pages.length ? "+  Scan another page" : "Start scanning  →"
                            primary: true; Layout.fillWidth: true; Layout.topMargin: 8; implicitHeight: 48
                            enabled: studio.operation.indexOf("Scanning") === 0 || (!studio.busy && studio.online)
                            onClicked: {
                                if (studio.operation.indexOf("Scanning") === 0) studio.cancelScan()
                                else studio.scan(scanSource.currentText, scanMode.currentText, parseInt(scanDpi.currentText), scanSize.currentText, brightness.value, contrast.value)
                            }
                        }
                        Action { text: "Connect scanner"; visible: !studio.online; enabled: !studio.busy; Layout.fillWidth: true; onClicked: studio.discover() }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                        RowLayout {
                            Caption { text: "DOCUMENT PREVIEW" }
                            Item { Layout.fillWidth: true }
                            Label { text: studio.pages.length + (studio.pages.length === 1 ? " PAGE" : " PAGES"); font.pixelSize: 10; color: win.muted; font.letterSpacing: 1 }
                            Action { text: "New"; implicitHeight: 30; implicitWidth: 60; enabled: !studio.busy && studio.pages.length > 0; onClicked: clearDialog.open() }
                            Action { text: "Import"; implicitHeight: 30; implicitWidth: 70; enabled: !studio.busy; onClicked: importDialog.open() }
                        }
                        Panel {
                            id: previewPanel
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            color: Qt.alpha(win.fg, 0.018)
                            // Subtle alignment grid, drawn with native Qt Quick primitives.
                            Repeater {
                                model: 14
                                Rectangle {
                                    required property int index
                                    x: index * previewPanel.width / 13; y: 0; width: 1; height: previewPanel.height
                                    color: Qt.alpha(win.fg, 0.025)
                                }
                            }
                            Repeater {
                                model: 12
                                Rectangle {
                                    required property int index
                                    x: 0; y: index * previewPanel.height / 11; height: 1; width: previewPanel.width
                                    color: Qt.alpha(win.fg, 0.025)
                                }
                            }
                            Image {
                                id: documentImage
                                anchors.fill: parent; anchors.margins: 25
                                source: win.currentPage ? win.currentPage.url : ""
                                visible: studio.pages.length > 0
                                fillMode: Image.PreserveAspectFit; asynchronous: true; cache: false
                                sourceSize.width: 1400; sourceSize.height: 1800
                            }
                            ColumnLayout {
                                anchors.centerIn: parent; spacing: 14
                                visible: studio.pages.length === 0
                                Item {
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: 186; Layout.preferredHeight: 196
                                    Rectangle {
                                        x: 22; y: 9; width: 144; height: 174; radius: 10
                                        rotation: -7; color: Qt.alpha(win.accent, 0.07); border.color: Qt.alpha(win.accent, 0.15)
                                    }
                                    Rectangle {
                                        id: paperArt
                                        x: 19; y: 6; width: 144; height: 174; radius: 10
                                        color: win.bg; border.color: Qt.alpha(win.accent, 0.55)
                                        Column {
                                            x: 23; y: 28; spacing: 12
                                            Rectangle { width: 35; height: 5; radius: 3; color: win.accent }
                                            Rectangle { width: 93; height: 3; radius: 2; color: Qt.alpha(win.fg, 0.25) }
                                            Rectangle { width: 82; height: 3; radius: 2; color: Qt.alpha(win.fg, 0.18) }
                                            Rectangle { width: 91; height: 3; radius: 2; color: Qt.alpha(win.fg, 0.18) }
                                            Rectangle { width: 65; height: 3; radius: 2; color: Qt.alpha(win.fg, 0.18) }
                                            Rectangle { width: 91; height: 31; radius: 4; color: Qt.alpha(win.accent, 0.07); border.color: Qt.alpha(win.accent, 0.14) }
                                        }
                                        Rectangle {
                                            id: emptyBeam
                                            x: -12; y: 70; width: 168; height: 2; color: win.accent
                                            visible: studio.operation.indexOf("Scanning") === 0
                                            Rectangle { width: parent.width; height: 25; anchors.bottom: parent.top; gradient: Gradient { GradientStop { position: 0; color: "transparent" } GradientStop { position: 1; color: Qt.alpha(win.accent, 0.18) } } }
                                            SequentialAnimation on y {
                                                running: studio.operation.indexOf("Scanning") === 0 && !win.reducedMotion
                                                loops: Animation.Infinite
                                                NumberAnimation { from: 22; to: 157; duration: 1800; easing.type: Easing.InOutSine }
                                                NumberAnimation { from: 157; to: 22; duration: 1800; easing.type: Easing.InOutSine }
                                            }
                                        }
                                    }
                                    Rectangle {
                                        x: 139; y: 153; width: 36; height: 36; radius: 18; color: win.accent
                                        Label { anchors.centerIn: parent; text: "+"; font.pixelSize: 25; color: win.bg }
                                    }
                                }
                                Label { text: studio.operation.indexOf("Scanning") === 0 ? "Bringing your pages to life" : "Paper, meet pixels."; color: win.fg; font.pixelSize: 22; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter; font.letterSpacing: -0.5 }
                                Label { text: "Scan a page or import an image to get started."; color: win.muted; font.pixelSize: 12; Layout.alignment: Qt.AlignHCenter }
                            }
                            Rectangle {
                                anchors.fill: parent; color: Qt.alpha(win.bg, 0.5)
                                visible: studio.pages.length > 0 && studio.operation.indexOf("Scanning") === 0
                                BusyIndicator { anchors.centerIn: parent; running: parent.visible }
                            }
                        }
                        ListView {
                            id: thumbnails
                            visible: studio.pages.length > 0
                            Layout.fillWidth: true; Layout.preferredHeight: 78
                            orientation: ListView.Horizontal; spacing: 10; clip: true
                            model: studio.pages
                            delegate: Rectangle {
                                id: thumb
                                required property var modelData
                                required property int index
                                width: 59; height: 76; radius: 6
                                color: Qt.alpha(win.fg, 0.04)
                                border.color: win.selectedPage === index ? win.accent : win.edge
                                border.width: win.selectedPage === index ? 2 : 1
                                Image { anchors.fill: parent; anchors.margins: 6; anchors.bottomMargin: 21; source: thumb.modelData.url; fillMode: Image.PreserveAspectFit; sourceSize.width: 100; asynchronous: true; cache: false }
                                Label { anchors.bottom: parent.bottom; anchors.bottomMargin: 4; anchors.horizontalCenter: parent.horizontalCenter; text: thumb.index + 1; font.pixelSize: 10; color: win.selectedPage === thumb.index ? win.accent : win.muted }
                                MouseArea { anchors.fill: parent; onClicked: win.selectedPage = thumb.index; cursorShape: Qt.PointingHandCursor }
                            }
                        }
                        RowLayout {
                            visible: studio.pages.length > 0
                            Action { text: "Rotate ↻"; implicitHeight: 34; enabled: !studio.busy; onClicked: studio.rotatePage(win.selectedPage) }
                            Action { text: "←"; implicitHeight: 34; implicitWidth: 34; enabled: !studio.busy && win.selectedPage > 0; Accessible.name: "Move page earlier"; onClicked: { studio.movePage(win.selectedPage, -1); win.selectedPage-- } }
                            Action { text: "→"; implicitHeight: 34; implicitWidth: 34; enabled: !studio.busy && win.selectedPage < studio.pages.length - 1; Accessible.name: "Move page later"; onClicked: { studio.movePage(win.selectedPage, 1); win.selectedPage++ } }
                            Item { Layout.fillWidth: true }
                            Action { text: "Remove"; danger: true; implicitHeight: 34; enabled: !studio.busy; onClicked: { studio.removePage(win.selectedPage); win.selectedPage = Math.max(0, Math.min(win.selectedPage, studio.pages.length - 1)) } }
                        }
                        RowLayout {
                            Layout.topMargin: 2
                            Label { text: "PDF · PNG · JPEG"; color: win.muted; font.pixelSize: 11 }
                            Item { Layout.fillWidth: true }
                            Action { text: "Print scan"; enabled: !studio.busy && studio.pages.length > 0; onClicked: { studio.useScanForPrint(); win.section = 1 } }
                            Action { text: "Export document  ↗"; primary: true; enabled: !studio.busy && studio.pages.length > 0; onClicked: exportDialog.open() }
                        }
                    }
                }

                // PRINT
                ColumnLayout {
                    spacing: 20
                    Panel {
                        Layout.fillWidth: true; implicitHeight: 140
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 28; spacing: 22
                            Label { text: "▤"; color: win.accent; font.pixelSize: 56 }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 8
                                Caption { text: "PRINT FILE" }
                                Label { text: studio.printFile ? studio.printFile.split("/").pop() : "Choose your next print"; color: win.fg; font.pixelSize: 21; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                Label { text: studio.printFile || "PDFs, images and text documents"; color: win.muted; font.pixelSize: 12; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            }
                            Action { text: "Choose file"; enabled: !studio.busy; onClicked: printDialog.open() }
                        }
                    }
                    RowLayout {
                        spacing: 24; Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            Caption { text: "PRINTER" }
                            Field { id: queue; model: studio.queues; enabled: !studio.busy; displayText: count ? currentText : "No Brother queue configured" }
                        }
                        ColumnLayout {
                            Layout.preferredWidth: 135
                            Caption { text: "COPIES" }
                            SpinBox { id: copies; from: 1; to: 99; value: 1; editable: true; Layout.fillWidth: true; implicitHeight: 42; enabled: !studio.busy }
                        }
                        ColumnLayout {
                            Layout.preferredWidth: 150
                            Caption { text: "PAPER" }
                            Field { id: printPaper; model: ["A4", "Letter"]; enabled: !studio.busy }
                        }
                    }
                    RowLayout {
                        CheckBox { id: duplex; text: "Print on both sides"; checked: true; enabled: !studio.busy }
                        Item { Layout.fillWidth: true }
                        Label { text: "Pages"; color: win.muted }
                        TextInput { id: pageRange; placeholderText: "All · e.g. 1-3,5"; Layout.preferredWidth: 180; enabled: !studio.busy }
                        Action { text: "Print document  →"; primary: true; enabled: !studio.busy && studio.queues.length > 0 && studio.printFile.length > 0; onClicked: studio.printDocument(queue.currentText, copies.value, duplex.checked, printPaper.currentText, pageRange.text) }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: win.edge; Layout.topMargin: 5; Layout.bottomMargin: 5 }
                    RowLayout {
                        Caption { text: "PRINT QUEUE" }
                        Item { Layout.fillWidth: true }
                        Action { text: "Refresh"; implicitHeight: 32; enabled: !studio.busy; onClicked: studio.refresh_printer() }
                        Action { text: "Add Brother printer"; visible: studio.queues.length === 0; enabled: !studio.busy; onClicked: setupDialog.open() }
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 10
                        model: studio.jobs
                        delegate: Panel {
                            id: job
                            required property var modelData
                            width: ListView.view.width; height: 68
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 14
                                Label { text: job.modelData.detail; color: win.fg; elide: Text.ElideRight; Layout.fillWidth: true; font.pixelSize: 12 }
                                Action { text: "Cancel job"; danger: true; enabled: !studio.busy; onClicked: studio.cancelJob(job.modelData.id) }
                            }
                        }
                        Label { anchors.centerIn: parent; visible: studio.jobs.length === 0; text: "No active print jobs"; color: win.muted }
                    }
                }

                // DOCUMENTS
                ColumnLayout {
                    spacing: 16
                    RowLayout {
                        Caption { text: "RECENT EXPORTS" }
                        Item { Layout.fillWidth: true }
                        Action { text: "Open Documents folder ↗"; onClicked: studio.openFolder() }
                    }
                    Label { text: "Your documents stay on this computer. Click a file to open it."; color: win.muted; font.pixelSize: 13 }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12; clip: true
                        model: studio.recent
                        delegate: Panel {
                            id: recentItem
                            required property string modelData
                            width: ListView.view.width; height: 86
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 20; spacing: 18
                                Label { text: "▥"; color: win.accent; font.pixelSize: 29 }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: recentItem.modelData.split("/").pop(); color: win.fg; font.weight: Font.DemiBold; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                    Label { text: recentItem.modelData; color: win.muted; font.pixelSize: 11; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                }
                                Action { text: "Open ↗"; onClicked: studio.openFile(recentItem.modelData) }
                            }
                        }
                        ColumnLayout {
                            anchors.centerIn: parent; visible: studio.recent.length === 0; spacing: 12
                            Label { text: "A fresh start."; color: win.fg; font.pixelSize: 26; Layout.alignment: Qt.AlignHCenter }
                            Label { text: "Export your first scan and it will appear here."; color: win.muted; Layout.alignment: Qt.AlignHCenter }
                        }
                    }
                }

                // DEVICE
                ScrollView {
                    clip: true; contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width; spacing: 18
                        Panel {
                            Layout.fillWidth: true; implicitHeight: 168
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 28; spacing: 24
                                Image { source: "../../assets/brother-studio.svg"; Layout.preferredWidth: 80; Layout.preferredHeight: 80 }
                                ColumnLayout {
                                    spacing: 8; Layout.fillWidth: true
                                    Caption { text: "YOUR NETWORK WORKHORSE" }
                                    Label { text: "Brother MFC-L2800DW"; color: win.fg; font.pixelSize: 24; font.weight: Font.DemiBold }
                                    Label { text: "Mono laser printer · colour scanner · copier · fax"; color: win.muted; font.pixelSize: 12 }
                                    Label { text: studio.online ? "Scanner connected via SANE / AirScan" : "Connect to load scanner capabilities"; color: studio.online ? win.green : win.muted; font.pixelSize: 12 }
                                }
                            }
                        }
                        Caption { text: "CONNECTION"; Layout.topMargin: 6 }
                        RowLayout {
                            TextInput { id: ipInput; text: studio.ip; Layout.preferredWidth: 220; enabled: !studio.busy; placeholderText: "Printer IP address"; Accessible.name: "Printer IP address" }
                            Action { text: "Save & connect"; enabled: !studio.busy; onClicked: studio.setIp(ipInput.text) }
                            Item { Layout.fillWidth: true }
                            Action { text: "Refresh connection"; enabled: !studio.busy; onClicked: studio.discover() }
                        }
                        Caption { text: "DEVICE CONTROLS"; Layout.topMargin: 10 }
                        Panel {
                            Layout.fillWidth: true; implicitHeight: 120
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 20
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 8
                                    Label { text: "Advanced settings & supplies"; color: win.fg; font.weight: Font.DemiBold }
                                    Label { text: "Toner, drum, network, fax and administrator settings.\nSign in securely in Brother's web interface."; color: win.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12; lineHeight: 1.3 }
                                }
                                Action { text: "Open Brother settings ↗"; onClicked: studio.openDevice() }
                            }
                        }
                        Panel {
                            Layout.fillWidth: true; implicitHeight: 108
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 20
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 8
                                    Label { text: "Driverless network printing"; color: win.fg; font.weight: Font.DemiBold }
                                    Label { text: studio.queues.length ? "Brother queue: " + studio.queues.join(", ") : "Add the IPP printer to CUPS. Administrator authentication may be required."; color: win.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
                                }
                                Action { text: studio.queues.length ? "Refresh queue" : "Add printer"; enabled: !studio.busy; onClicked: { if (studio.queues.length) studio.refresh_printer(); else setupDialog.open() } }
                            }
                        }
                        Caption { text: "GOOD TO KNOW"; Layout.topMargin: 8 }
                        Label {
                            text: "• The document feeder scans one side per pass. For two-sided originals, scan the reverse sides and reorder pages before export.\n• Copy a document through Scan → Print scan, or use the printer's physical controls.\n• Fax setup lives in Brother settings; sending a fax uses the device panel.\n• Scanning needs sane-airscan; printing needs cups and a configured queue."
                            wrapMode: Text.WordWrap; Layout.fillWidth: true; color: win.muted; font.pixelSize: 12; lineHeight: 1.6
                        }
                        CheckBox { text: "Reduce interface animations"; checked: win.reducedMotion; onToggled: win.reducedMotion = checked }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 49
                color: Qt.alpha(win.fg, 0.02)
                Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: win.edge }
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 30; anchors.rightMargin: 30; spacing: 12
                    BusyIndicator { running: studio.busy; visible: studio.busy; Layout.preferredWidth: 20; Layout.preferredHeight: 20 }
                    Rectangle { visible: !studio.busy; width: 5; height: 5; radius: 3; color: studio.error ? win.red : win.green }
                    Label {
                        text: studio.message; color: studio.error ? win.red : win.muted; font.pixelSize: 11
                        Layout.fillWidth: true; elide: Text.ElideRight
                        ToolTip.visible: statusHover.hovered
                        ToolTip.text: studio.message
                        HoverHandler { id: statusHover }
                    }
                    ProgressBar { visible: studio.operation.indexOf("Scanning") === 0; value: studio.progress; Layout.preferredWidth: 100; implicitHeight: 4 }
                    Label { text: "LOCAL. PRIVATE. YOURS."; color: win.muted; font.pixelSize: 8; font.letterSpacing: 1.4; opacity: 0.6 }
                }
            }
        }
    }
}
