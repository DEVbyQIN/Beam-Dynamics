$ENV{'CMAPFONTS'} = './fonts:' . ($ENV{'CMAPFONTS'} // '');
$xelatex = 'xelatex -no-pdf -interaction=nonstopmode -halt-on-error %O %S';
