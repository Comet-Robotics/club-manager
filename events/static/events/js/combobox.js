// Input-focused combobox controller shared by the event sign-in fields.
function createCombobox(config) {
    const input = config.input;
    let activeIndex = null;
    let defaultToFirst = false;
    let trigger = 'keyboard';
    let pointer = null;

    function isSelectable() {
        return !input.disabled && !input.readOnly;
    }
    function options() {
        return config.getOptions();
    }
    function resolvedActive() {
        if (defaultToFirst && activeIndex === null) {
            const first = options().findIndex(function (option) { return !option.disabled; });
            if (first !== -1) return first;
        }
        return activeIndex;
    }
    function setExpanded(value) {
        input.setAttribute('aria-expanded', value ? 'true' : 'false');
    }
    function applyActive() {
        const all = options();
        const index = resolvedActive();
        all.forEach(function (option, i) { option.classList.toggle('is-active', i === index); });
        const active = index === null ? null : all[index];
        if (active && active.id) input.setAttribute('aria-activedescendant', active.id);
        else input.removeAttribute('aria-activedescendant');
        if (active && active.scrollIntoView) {
            requestAnimationFrame(function () { active.scrollIntoView({ block: 'nearest' }); });
        }
    }
    function goTo(index, nextTrigger) {
        trigger = nextTrigger || 'keyboard';
        defaultToFirst = false;
        activeIndex = index;
        applyActive();
    }
    function moveNext() {
        const all = options();
        const from = resolvedActive();
        if (from === null) goTo(0);
        else if (from + 1 < all.length) goTo(from + 1);
        else applyActive();
    }
    function movePrevious() {
        const all = options();
        const from = resolvedActive();
        if (from === null) goTo(all.length - 1);
        else if (from - 1 >= 0) goTo(from - 1);
        else applyActive();
    }
    function close() {
        activeIndex = null;
        defaultToFirst = false;
        trigger = 'keyboard';
        setExpanded(false);
        applyActive();
        if (!config.hasSelection()) config.onClear();
    }
    function select(option) {
        setExpanded(false);
        config.onSelect(option, trigger === 'pointer');
        goTo(null);
    }
    function sync() {
        const all = options();
        const listbox = config.getList();
        if (isSelectable() && all.length && listbox && listbox.id) input.setAttribute('aria-controls', listbox.id);
        else input.removeAttribute('aria-controls');
        setExpanded(all.length > 0 && isSelectable());
        activeIndex = null;
        applyActive();
    }
    function markTyping() {
        defaultToFirst = true;
        trigger = 'keyboard';
        applyActive();
    }
    input.addEventListener('keydown', function (event) {
        if (!isSelectable()) return;
        const all = options();
        switch (event.key) {
            case 'Enter':
                if (!all.length || event.isComposing) return;
                if (config.enterSubmits && resolvedActive() === null) return;
                event.preventDefault();
                event.stopPropagation();
                if (resolvedActive() !== null) select(all[resolvedActive()]);
                else close();
                break;
            case 'ArrowDown':
                if (!all.length) return;
                event.preventDefault();
                event.stopPropagation();
                moveNext();
                break;
            case 'ArrowUp':
                if (!all.length) return;
                event.preventDefault();
                event.stopPropagation();
                movePrevious();
                break;
            case 'Home':
            case 'PageUp':
                if (!all.length || (event.key === 'Home' && event.shiftKey)) return;
                event.preventDefault();
                event.stopPropagation();
                goTo(0);
                break;
            case 'End':
            case 'PageDown':
                if (!all.length) return;
                event.preventDefault();
                event.stopPropagation();
                goTo(all.length - 1);
                break;
            case 'Escape':
                if (!all.length) return;
                event.preventDefault();
                event.stopPropagation();
                close();
                break;
            case 'Tab':
                if (all.length && config.tabSelects && resolvedActive() !== null) {
                    event.preventDefault();
                    select(all[resolvedActive()]);
                }
                break;
        }
    });
    input.addEventListener('blur', function (event) {
        if (!isSelectable()) return;
        const related = event.relatedTarget;
        const list = config.getList();
        if (related && list && (related === list || list.contains(related))) return;
        if (config.button && related && (related === config.button || config.button.contains(related))) return;
        close();
    });
    document.addEventListener('mousedown', function (event) {
        const list = config.getList();
        if (!list || !list.contains(event.target)) return;
        event.preventDefault();
        if (!isSelectable()) return;
        const option = event.target.closest('[role="option"]');
        if (!option || option.disabled || event.button !== 0) return;
        select(option);
    });
    document.addEventListener('pointermove', function (event) {
        const list = config.getList();
        if (!list || !list.contains(event.target)) return;
        if (!isSelectable() || !options().length) return;
        const wasMoved = pointer && pointer.x === event.clientX && pointer.y === event.clientY;
        pointer = { x: event.clientX, y: event.clientY };
        if (wasMoved) return;
        const option = event.target.closest('[role="option"]');
        if (!option || option.disabled) return;
        const index = options().indexOf(option);
        if (index !== resolvedActive() || trigger !== 'pointer') goTo(index, 'pointer');
    });
    document.addEventListener('pointerout', function (event) {
        const list = config.getList();
        if (!list || !list.contains(event.target)) return;
        const next = event.relatedTarget && event.relatedTarget.closest && event.relatedTarget.closest('[role="option"]');
        if (next) return;
        if (trigger === 'pointer' && resolvedActive() !== null) goTo(null, 'pointer');
    });
    document.body.addEventListener('htmx:afterSwap', function (event) {
        if (config.matches(event.detail.target)) sync();
    });
    return { sync: sync, markTyping: markTyping };
}
