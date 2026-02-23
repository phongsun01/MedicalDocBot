echo "Test copy PDF"
cp "dummy_test.json" "test.pdf" 
sleep 2
echo "Some content" > "test.pdf"
sleep 5
tail -n 20 logs/watcher.log
