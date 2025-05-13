from django.urls import path
from .views import file_tree_view, download_file, upload_file, delete_item, create_folder, edit_file, extract_archive, \
    move_item, login_view, logout_view, download_archive, keep_alive

urlpatterns = [
    path('files/', file_tree_view, name='file_tree'),
    path('files/download/<path:path>/', download_file, name='download_file'),
    path('upload/', upload_file, name='upload_file'),
    path('login/', login_view, name='login'),
    path('delete/', delete_item, name='delete_item'),
    path('create-folder/', create_folder, name='create_folder'),
    path("edit-file/", edit_file, name="edit_file"),
    path('extract/', extract_archive, name='extract_archive'),
    path('move_item/', move_item, name='move_item'),
    path('logout/', logout_view, name='logout'),
    path('download-archive/', download_archive, name='download_archive'),
    path('keep-alive/', keep_alive, name='keep_alive'),

]
