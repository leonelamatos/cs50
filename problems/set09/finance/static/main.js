let search = document.getElementById('search');
let matchList = document.getElementById('match-list');
let listContainer = document.getElementById('list-container');
let symbolSelection = null;

// search for company symbol name and filtered
const searchSymbol = async (searchText) => {
    // const symbols = JSON.parse('{{data.result | tojson}}');
    const symbols = JSON.parse(data);
    listContainer.classList.remove('hide');
    listContainer.classList.add('show');
    matchList.innerHTML = '';

    // Get matches to current  text input
    let matches = symbols.filter((symbol) => {
        const regex = new RegExp(`^${searchText}`, 'gi');
        return symbol.s.match(regex) || symbol.n.match(regex);
    });

    if (searchText.length == 0) {
        matches = [];
    }
    outputHtml(matches);
    setQuoteRequestValue()
};

function setSearchValue() {
    const symbolName = this.dataset.symbol;
    search.value = symbolName;
    matchList.innerHTML = '';
    listContainer.classList.add('hide');
    listContainer.classList.remove('show');
}

const setQuoteRequestValue = () => {
    symbolSelection = document.querySelectorAll('.list-item');
    
    // Set the value for the input field
    symbolSelection.forEach((symbol) => {
        symbol.addEventListener('click', setSearchValue);
    });
}
const outputHtml = (matches) => {
    if (matches.length > 0) {
        const html = matches
            .map(
                (match) => `
        <div class="list-item list-group-item text-start lh-1 hstack gap-3 py-3" data-symbol="${match.s}" >
            <h6 class="mb-0  text-primary" style="width: 50px">${match.s}</h6>
            <div class="vr pl-3"></div>
            <small class="text-secondary fw-bold fs-6">${match.n}</small>
        </div>
            `,
            )
            .join('');
        matchList.innerHTML = html;
    } else {
        
        listContainer.classList.remove('show');
        listContainer.classList.add('hide');
    }
};



search.addEventListener('input', () => searchSymbol(search.value));